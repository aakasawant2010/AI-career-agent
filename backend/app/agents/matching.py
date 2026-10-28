from __future__ import annotations

from dataclasses import dataclass, field

from app.models.candidate_intelligence import CandidateIntelligence
from app.models.job import Job


@dataclass
class MatchState:
    candidate: CandidateIntelligence
    job: Job
    weights: dict[str, float]
    role_score: float = 0
    skills_score: float = 0
    experience_score: float = 0
    location_score: float = 0
    salary_score: float = 0
    notice_score: float = 0
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    explanation: str = ""


def _norm(value: str) -> str:
    value = value.lower().strip()
    aliases = {"gen ai": "generative ai", "genai": "generative ai", "postgres": "postgresql", "k8s": "kubernetes"}
    return aliases.get(value, value)


def _set(values) -> set[str]:
    return {_norm(str(x)) for x in (values or []) if str(x).strip()}


def role_match(state: MatchState) -> MatchState:
    roles = _set(state.candidate.target_roles) | _set((state.candidate.career_profile or {}).get("target_roles"))
    title = _norm(state.job.title)
    if not roles:
        state.role_score = 50
        return state
    exact = any(role == title for role in roles)
    partial = any(role in title or title in role for role in roles)
    if exact:
        state.role_score = 100
    elif partial:
        state.role_score = 85
    else:
        # Useful semantic-ish overlap without an LLM dependency.
        tokens = set(title.split())
        best = max((len(tokens & set(role.split())) / max(1, len(set(role.split()))) for role in roles), default=0)
        state.role_score = min(70, best * 100)
    return state


def skill_match(state: MatchState) -> MatchState:
    candidate_skills = _set(state.candidate.core_skills) | _set(state.candidate.technologies)
    required = _set(state.job.skills) | _set(state.job.technologies)
    if not required:
        state.skills_score = 70
        return state
    matched = sorted(candidate_skills & required)
    missing = sorted(required - candidate_skills)
    state.matched_skills = matched
    state.missing_skills = missing
    state.skills_score = len(matched) / len(required) * 100
    return state


def experience_match(state: MatchState) -> MatchState:
    candidate_years = (state.candidate.career_profile or {}).get("total_experience_years")
    if candidate_years is None:
        candidate_years = state.candidate.resume_intelligence.get("total_experience_years")
    minimum = state.job.experience_min_years
    maximum = state.job.experience_max_years
    if minimum is None:
        state.experience_score = 80
    elif candidate_years is None:
        state.experience_score = 50
        state.risks.append("Candidate experience could not be verified against the job requirement")
    elif candidate_years >= minimum:
        state.experience_score = 100 if maximum is None or candidate_years <= maximum + 2 else 85
    else:
        gap = minimum - candidate_years
        state.experience_score = max(0, 100 - gap * 35)
        state.risks.append(f"Experience gap: approximately {gap:.1f} year(s)")
    return state


def location_match(state: MatchState) -> MatchState:
    preferred = _set(state.candidate.preferred_locations) | _set((state.candidate.career_profile or {}).get("preferred_locations"))
    job_location = _norm(state.job.location or "")
    if state.job.work_mode == "remote":
        state.location_score = 100
        return state
    if not preferred or not job_location:
        state.location_score = 60
        return state
    if any(loc in job_location or job_location in loc for loc in preferred):
        state.location_score = 100
    else:
        state.location_score = 25
        state.risks.append(f"Location may not match preferences: {state.job.location}")
    return state


def salary_match(state: MatchState) -> MatchState:
    profile = state.candidate.career_profile or {}
    candidate_min = profile.get("min_salary_lpa")
    if candidate_min is None or (state.job.max_salary_lpa is None and state.job.min_salary_lpa is None):
        state.salary_score = 60
    elif state.job.max_salary_lpa is not None and state.job.max_salary_lpa >= candidate_min:
        state.salary_score = 100
    elif state.job.min_salary_lpa is not None and state.job.min_salary_lpa >= candidate_min:
        state.salary_score = 100
    else:
        state.salary_score = 20
        state.risks.append("Published salary may be below the candidate's minimum target")
    return state


def notice_match(state: MatchState) -> MatchState:
    candidate_notice = (state.candidate.career_profile or {}).get("notice_period_days")
    if candidate_notice is None or state.job.notice_period_days is None:
        state.notice_score = 70
    elif candidate_notice <= state.job.notice_period_days:
        state.notice_score = 100
    else:
        state.notice_score = 30
        state.risks.append("Notice period may exceed the job's stated requirement")
    return state


def calculate_score(state: MatchState) -> float:
    weighted = (
        state.role_score * state.weights["role"]
        + state.skills_score * state.weights["skills"]
        + state.experience_score * state.weights["experience"]
        + state.location_score * state.weights["location"]
        + state.salary_score * state.weights["salary"]
        + state.notice_score * state.weights["notice"]
    ) / sum(state.weights.values())
    return round(max(0, min(100, weighted)), 2)


def recommendation(score: float) -> str:
    if score >= 85:
        return "strong_match"
    if score >= 70:
        return "good_match"
    if score >= 55:
        return "possible_match"
    return "low_match"


def build_explanation(state: MatchState, score: float) -> str:
    matched = ", ".join(state.matched_skills[:8]) or "no strong skill overlap detected"
    missing = ", ".join(state.missing_skills[:6])
    text = f"Match score {score}/100. Strongest matching skills: {matched}."
    if missing:
        text += f" Main skill gaps: {missing}."
    if state.risks:
        text += f" Risks: {'; '.join(state.risks[:3])}."
    return text


def run_matching_workflow(candidate: CandidateIntelligence, job: Job, weights: dict[str, float] | None = None) -> dict:
    default_weights = {"role": 25, "skills": 35, "experience": 15, "location": 10, "salary": 10, "notice": 5}
    weights = weights or default_weights
    if abs(sum(weights.values()) - 100) > 0.001:
        raise ValueError("Match weights must add up to 100")
    state = MatchState(candidate=candidate, job=job, weights=weights)
    for node in (role_match, skill_match, experience_match, location_match, salary_match, notice_match):
        node(state)
    score = calculate_score(state)
    rec = recommendation(score)
    state.explanation = build_explanation(state, score)
    return {
        "score": score,
        "recommendation": rec,
        "breakdown": {
            "role": round(state.role_score, 2),
            "skills": round(state.skills_score, 2),
            "experience": round(state.experience_score, 2),
            "location": round(state.location_score, 2),
            "salary": round(state.salary_score, 2),
            "notice": round(state.notice_score, 2),
            "weights": weights,
        },
        "matched_skills": state.matched_skills,
        "missing_skills": state.missing_skills,
        "risks": state.risks,
        "explanation": state.explanation,
    }
