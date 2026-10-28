from sqlalchemy.orm import Session

from app.models.career_profile import CareerProfile
from app.models.project import Project
from app.models.resume import Resume
from app.models.resume_intelligence import ResumeIntelligence
from app.models.candidate_intelligence import CandidateIntelligence


def build_candidate_intelligence(
    user_id,
    db: Session,
):
    career_profile = (
        db.query(CareerProfile)
        .filter(CareerProfile.user_id == user_id)
        .first()
    )

    if not career_profile:
        raise ValueError("Career profile not found")

    active_resume = (
        db.query(Resume)
        .filter(
            Resume.user_id == user_id,
            Resume.is_active == True,
        )
        .first()
    )

    if not active_resume:
        raise ValueError("Active resume not found")

    resume_intelligence = (
        db.query(ResumeIntelligence)
        .filter(
            ResumeIntelligence.resume_id == active_resume.id
        )
        .first()
    )

    if not resume_intelligence:
        raise ValueError("Resume intelligence not found")

    projects = (
        db.query(Project)
        .filter(Project.user_id == user_id)
        .all()
    )

    candidate = (
        db.query(CandidateIntelligence)
        .filter(CandidateIntelligence.user_id == user_id)
        .first()
    )

    if not candidate:
        candidate = CandidateIntelligence(
            user_id=user_id
        )
        db.add(candidate)

    candidate.career_profile = {
        "target_roles": career_profile.target_roles,
        "preferred_locations": career_profile.preferred_locations,
        "work_preference": career_profile.work_preference,
        "min_salary_lpa": career_profile.min_salary_lpa,
        "max_salary_lpa": career_profile.max_salary_lpa,
        "notice_period_days": career_profile.notice_period_days,
        "total_experience_years": career_profile.total_experience_years,
        "skills": career_profile.skills,
        "certifications": career_profile.certifications,
        "education": career_profile.education,
        "actively_looking": career_profile.actively_looking,
    }

    candidate.resume_intelligence = {
        "skills": resume_intelligence.skills,
        "experience": resume_intelligence.experience,
        "education": resume_intelligence.education,
        "projects": resume_intelligence.projects,
        "certifications": resume_intelligence.certifications,
        "job_titles": resume_intelligence.job_titles,
        "technologies": resume_intelligence.technologies,
        "total_experience_years": resume_intelligence.total_experience_years,
        "summary": resume_intelligence.summary,
    }

    candidate.projects = [
        {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "technologies": project.technologies,
            "github_url": project.github_url,
            "live_url": project.live_url,
            "role": project.role,
            "featured": project.featured,
        }
        for project in projects
    ]

    # Combine skills from Career Profile + Resume Intelligence
    candidate.core_skills = sorted(
        set(
            (career_profile.skills or [])
            + (resume_intelligence.skills or [])
        )
    )

    # Combine technologies from Resume Intelligence + Projects
    technologies = set(
        resume_intelligence.technologies or []
    )

    for project in projects:
        technologies.update(project.technologies or [])

    candidate.technologies = sorted(technologies)

    candidate.target_roles = (
        career_profile.target_roles or []
    )

    candidate.preferred_locations = (
        career_profile.preferred_locations or []
    )

    candidate.professional_summary = (
        resume_intelligence.summary
    )

    db.commit()
    db.refresh(candidate)

    return candidate