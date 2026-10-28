"""Phase 9 – interview session orchestration (DB + optional LLM)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import interview as agent
from app.models.application import Application
from app.models.candidate_intelligence import CandidateIntelligence
from app.models.interview import InterviewQuestion, InterviewSession
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.project import Project
from app.models.user import AuditLog
from app.services import llm

log = logging.getLogger("app.interview")


class InterviewError(ValueError):
    """Raised for user-facing problems (maps to 4xx in the API layer)."""


# ------------------------------------------------------------------------ helpers


def _job_text(job: Job) -> str:
    return f"{job.title} at {job.company}\n{(job.description or '')[:2500]}\n{(job.requirements or '')[:1500]}"


def _candidate_context(db: Session, user_id, job: Job) -> dict:
    candidate = db.scalar(select(CandidateIntelligence).where(CandidateIntelligence.user_id == user_id))
    match = db.scalar(select(JobMatch).where(JobMatch.user_id == user_id, JobMatch.job_id == job.id))
    projects: list[dict] = []
    if candidate and candidate.projects:
        projects = [p for p in candidate.projects if isinstance(p, dict)]
    if not projects:
        rows = db.scalars(select(Project).where(Project.user_id == user_id).order_by(Project.featured.desc()))
        projects = [{"name": p.name, "technologies": p.technologies or []} for p in rows]
    return {
        "skills": list({*(candidate.core_skills or []), *(candidate.technologies or [])}) if candidate else [],
        "missing": list(match.missing_skills or []) if match else [],
        "projects": projects,
        "summary": candidate.professional_summary if candidate else "",
    }


def _previous_fingerprints(db: Session, user_id, job_id) -> set[str]:
    rows = db.scalars(
        select(InterviewQuestion.question)
        .join(InterviewSession, InterviewSession.id == InterviewQuestion.session_id)
        .where(InterviewSession.user_id == user_id, InterviewSession.job_id == job_id)
    )
    return {agent.question_fingerprint(q) for q in rows}


def _llm_questions(job: Job, ctx: dict, mode: str, difficulty: str, count: int) -> list[agent.GeneratedQuestion]:
    """Ask the model for tailored questions. Anything malformed is dropped silently."""
    system = (
        "You are a senior interviewer. Return ONLY JSON: "
        '{"questions":[{"category":"technical|system_design|project|behavioral|role_fit|gap",'
        '"skill":"string or null","question":"string",'
        '"expected_points":[{"label":"what a good answer covers","keywords":["lowercase","keywords"]}]}]}. '
        "Each question needs 3-5 expected_points with 2-5 keywords each. "
        "Only reference candidate projects and skills that appear in the provided context; never invent experience."
    )
    user = (
        f"Job:\n{_job_text(job)}\n\nRequired skills: {', '.join(job.skills or [])}\n"
        f"Candidate skills: {', '.join(ctx['skills'][:25])}\n"
        f"Candidate projects: {', '.join(str(p.get('name')) for p in ctx['projects'][:6])}\n"
        f"Skill gaps: {', '.join(ctx['missing'][:6])}\n"
        f"Mode: {mode}. Difficulty: {difficulty}. Number of questions: {count}."
    )
    data = llm.complete_json(system, user)
    out: list[agent.GeneratedQuestion] = []
    for item in (data or {}).get("questions", []) if isinstance(data, dict) else []:
        try:
            category = str(item["category"])
            text = str(item["question"]).strip()
            points = [
                {"label": str(p["label"]), "keywords": [str(k).lower() for k in p["keywords"]][:6]}
                for p in item["expected_points"]
            ][:6]
        except (KeyError, TypeError):
            continue
        if category not in agent.CATEGORIES or len(text) < 15 or not points:
            continue
        if any(not p["keywords"] for p in points):
            continue
        skill = item.get("skill")
        out.append(agent.GeneratedQuestion(category, text, points, str(skill) if skill else None, "llm"))
    return out[:count]


# ------------------------------------------------------------------------ session


def create_session(
    db: Session,
    user_id,
    *,
    job_id=None,
    application_id=None,
    mode: str = "mixed",
    difficulty: str = "medium",
    num_questions: int = 6,
) -> InterviewSession:
    application = None
    if application_id is not None:
        application = db.get(Application, application_id)
        if application is None or application.user_id != user_id:
            raise LookupError("Application not found")
        if job_id is not None and job_id != application.job_id:
            raise InterviewError("job_id does not match the application's job")
        job_id = application.job_id
    job = db.get(Job, job_id)
    if job is None:
        raise LookupError("Job not found")

    ctx = _candidate_context(db, user_id, job)
    exclude = _previous_fingerprints(db, user_id, job.id)

    generated: list[agent.GeneratedQuestion] = []
    if llm.is_configured():
        generated = _llm_questions(job, ctx, mode, difficulty, num_questions)
    if len(generated) < num_questions:
        taken = {agent.question_fingerprint(q.question) for q in generated}
        fallback = agent.generate_questions(
            job_title=job.title,
            company=job.company,
            job_skills=list({*(job.skills or []), *(job.technologies or [])}),
            candidate_skills=ctx["skills"],
            missing_skills=ctx["missing"],
            projects=ctx["projects"],
            mode=mode,
            difficulty=difficulty,
            count=num_questions,
            exclude=exclude | taken,
        )
        for q in fallback:
            if len(generated) >= num_questions:
                break
            if agent.question_fingerprint(q.question) not in taken:
                generated.append(q)
    if not generated:
        raise InterviewError("Could not generate questions for this job")

    session = InterviewSession(
        user_id=user_id, job_id=job.id, application_id=application.id if application else None,
        mode=mode, difficulty=difficulty,
    )
    db.add(session)
    db.flush()
    for position, q in enumerate(generated, start=1):
        db.add(
            InterviewQuestion(
                session_id=session.id, position=position, category=q.category, skill=q.skill,
                question=q.question, expected_points=q.expected_points, difficulty=difficulty,
                source=q.source,
            )
        )
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, user_id, session_id) -> InterviewSession:
    session = db.get(InterviewSession, session_id)
    if session is None or session.user_id != user_id:
        raise LookupError("Interview session not found")
    return session


def session_questions(db: Session, session_id) -> list[InterviewQuestion]:
    return list(
        db.scalars(
            select(InterviewQuestion)
            .where(InterviewQuestion.session_id == session_id)
            .order_by(InterviewQuestion.position)
        )
    )


def answer_question(db: Session, user_id, session_id, question_id, answer: str) -> InterviewQuestion:
    session = get_session(db, user_id, session_id)
    if session.status != "IN_PROGRESS":
        raise InterviewError("This session is already completed")
    question = db.get(InterviewQuestion, question_id)
    if question is None or question.session_id != session.id:
        raise LookupError("Question not found")

    feedback = agent.evaluate_answer(answer, question.expected_points, question.category)
    if llm.is_configured() and feedback["word_count"] >= 15:
        feedback = _blend_llm_feedback(question, answer, feedback)

    question.answer = answer
    question.score = feedback["score"]
    question.feedback = feedback
    question.answered_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(question)
    return question


def _blend_llm_feedback(question: InterviewQuestion, answer: str, base: dict) -> dict:
    system = (
        "You are a strict but fair interview coach. Return ONLY JSON: "
        '{"score": 0-100, "strengths": ["..."], "improvements": ["..."]}. '
        "Judge only what the candidate actually wrote; do not add claims for them."
    )
    user = (
        f"Question: {question.question}\n"
        f"Good answers cover: {'; '.join(p['label'] for p in question.expected_points)}\n"
        f"Candidate answer:\n{answer}"
    )
    data = llm.complete_json(system, user, max_tokens=600)
    try:
        llm_score = float(data["score"])  # type: ignore[index]
        if not 0 <= llm_score <= 100:
            return base
        strengths = [str(s) for s in data["strengths"]][:3]  # type: ignore[index]
        improvements = [str(s) for s in data["improvements"]][:3]  # type: ignore[index]
    except (TypeError, KeyError, ValueError):
        return base
    blended = round((base["score"] + llm_score) / 2, 1)
    return {
        **base,
        "score": blended,
        "rating": agent.rating_for(blended),
        "strengths": (strengths + base["strengths"])[:4],
        "improvements": (improvements + base["improvements"])[:5],
        "evaluator": "rule_based+llm",
        "llm_score": llm_score,
    }


def complete_session(db: Session, user_id, session_id) -> InterviewSession:
    session = get_session(db, user_id, session_id)
    if session.status == "COMPLETED":
        return session
    questions = session_questions(db, session.id)
    job = db.get(Job, session.job_id)
    ctx = _candidate_context(db, user_id, job) if job else {"missing": []}
    report = agent.build_report(
        [
            {"category": q.category, "skill": q.skill, "score": q.score, "feedback": q.feedback}
            for q in questions
        ],
        ctx["missing"],
    )
    session.status = "COMPLETED"
    session.overall_score = report["overall_score"]
    session.summary = report
    session.completed_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            user_id=user_id,
            action="interview.session_completed",
            detail={
                "session_id": str(session.id),
                "job_id": str(session.job_id),
                "application_id": str(session.application_id) if session.application_id else None,
                "overall_score": report["overall_score"],
            },
        )
    )
    db.commit()
    db.refresh(session)
    return session
