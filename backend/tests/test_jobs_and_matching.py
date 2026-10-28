from app.models.candidate_intelligence import CandidateIntelligence
from app.models.job import Job
from app.models.job_match import JobMatch


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def candidate_intelligence_payload():
    return {
        "career_profile": {
            "target_roles": ["Generative AI Engineer", "AI Engineer"],
            "preferred_locations": ["Pune", "Remote"],
            "min_salary_lpa": 17,
            "notice_period_days": 90,
            "total_experience_years": 3.5,
        },
        "resume_intelligence": {"total_experience_years": 3.0},
        "projects": [],
        "core_skills": ["python", "langchain", "langgraph", "rag", "fastapi", "aws"],
        "technologies": ["python", "langchain", "langgraph", "rag", "fastapi", "aws"],
        "target_roles": ["Generative AI Engineer", "AI Engineer"],
        "preferred_locations": ["Pune", "Remote"],
        "professional_summary": "AI engineer",
    }


def test_manual_job_import_list_and_match(client, tokens, db):
    candidate = CandidateIntelligence(user_id=None, **candidate_intelligence_payload())
    # user_id is filled from the authenticated user below
    from sqlalchemy import select
    from app.models.user import User
    user = db.scalar(select(User))
    candidate.user_id = user.id
    db.add(candidate)
    db.commit()

    payload = {
        "source": "manual",
        "external_id": "demo-1",
        "title": "Generative AI Engineer",
        "company": "Demo AI",
        "location": "Pune",
        "work_mode": "hybrid",
        "description": "We need a Generative AI Engineer with Python, LangChain, LangGraph, RAG, FastAPI and AWS. 3+ years experience. Salary 18-24 LPA.",
        "apply_url": "https://example.com/jobs/demo-1",
    }
    r = client.post("/jobs/import", headers=auth(tokens["access_token"]), json=payload)
    assert r.status_code == 200, r.text
    job = r.json()["jobs"][0]

    listed = client.get("/jobs?q=Generative", headers=auth(tokens["access_token"]))
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    matched = client.post(f"/jobs/{job['id']}/match", headers=auth(tokens["access_token"]))
    assert matched.status_code == 200, matched.text
    assert matched.json()["score"] >= 70
    assert matched.json()["recommendation"] in {"strong_match", "good_match"}

    recs = client.get("/jobs/recommendations", headers=auth(tokens["access_token"]))
    assert recs.status_code == 200
    assert recs.json()["total"] == 1


def test_job_import_deduplicates(client, tokens):
    payload = {
        "source": "manual",
        "external_id": "same-id",
        "title": "AI Engineer",
        "company": "Demo",
        "description": "Python and RAG role",
    }
    first = client.post("/jobs/import", headers=auth(tokens["access_token"]), json=payload)
    second = client.post("/jobs/import", headers=auth(tokens["access_token"]), json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["created"] == 1
    assert second.json()["updated"] == 1
