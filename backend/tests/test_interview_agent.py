"""Phase 9: interview agent – pure logic first, then the API flow."""

import pytest

from app.agents import interview as agent
from app.services import llm
from tests.helpers import add_candidate, auth, make_application, make_job, register_and_login, set_status, walk

GOOD_RAG_ANSWER = (
    "I would split documents into chunks of about 500 tokens with overlap, embed them and store the vectors in "
    "pgvector. For retrieval I use hybrid search with a reranker and top-k of 5 because pure vector search missed "
    "keyword matches. To control hallucination I ground every answer in the retrieved sources and return citations. "
    "I evaluate with a golden set measuring recall and faithfulness, for example 120 questions, and monitor in production."
)


def gen(**kw):
    args = dict(
        job_title="Generative AI Engineer", company="Demo AI",
        job_skills=["python", "rag", "fastapi", "aws"], candidate_skills=["python", "fastapi", "rag"],
        missing_skills=["aws"], projects=[{"name": "Career Agent", "technologies": ["FastAPI"]}],
        mode="mixed", difficulty="medium", count=6,
    )
    args.update(kw)
    return agent.generate_questions(**args)


# ------------------------------------------------------------------- generation


def test_generation_is_tailored_unique_and_sized():
    qs = gen()
    assert len(qs) == 6
    assert len({agent.question_fingerprint(q.question) for q in qs}) == 6
    cats = {q.category for q in qs}
    assert {"technical", "behavioral"} <= cats
    text = " ".join(q.question for q in qs)
    assert "Career Agent" in text  # grounded in a real project
    assert any(q.category == "gap" and q.skill == "aws" for q in gen(count=12))
    assert all(q.expected_points for q in qs)


def test_mode_limits_categories():
    assert {q.category for q in gen(mode="behavioral", count=8)} <= {"behavioral", "role_fit", "gap"}
    assert "behavioral" not in {q.category for q in gen(mode="technical", count=8)}


def test_exclude_avoids_repeating_previous_questions():
    first = gen(count=5)
    seen = {agent.question_fingerprint(q.question) for q in first}
    second = gen(count=5, exclude=seen)
    assert not seen & {agent.question_fingerprint(q.question) for q in second}


def test_unknown_skill_gets_generic_question_and_hard_adds_scale_probe():
    qs = gen(job_skills=["cobol"], candidate_skills=["cobol"], missing_skills=[], mode="technical", difficulty="hard", count=3)
    assert any("cobol" in q.question.lower() for q in qs)
    assert any("10x scale" in q.question for q in qs if q.category in {"technical", "system_design"})


def test_skill_aliases_are_normalised():
    qs = gen(job_skills=["GenAI", "Postgres"], candidate_skills=["genai", "postgres"], missing_skills=[], mode="technical", count=4)
    assert {q.skill for q in qs} >= {"generative ai", "postgresql"}


# ------------------------------------------------------------------- evaluation


def test_strong_answer_beats_weak_beats_empty():
    pts = agent.SKILL_BANK["rag"][0][1]
    strong = agent.evaluate_answer(GOOD_RAG_ANSWER, pts, "technical")
    weak = agent.evaluate_answer("I use a vector database and an LLM to answer questions from documents.", pts, "technical")
    empty = agent.evaluate_answer("", pts, "technical")
    assert strong["score"] >= 80 and strong["rating"] in {"good", "strong"}
    assert weak["score"] < strong["score"] - 25
    assert empty["score"] == 0 and empty["improvements"]
    assert strong["missing_points"] == [] and weak["missing_points"]


def test_short_answers_are_capped():
    r = agent.evaluate_answer("chunking embedding rerank evaluate", agent.SKILL_BANK["rag"][0][1], "technical")
    assert r["score"] <= 25 and any("too short" in i for i in r["improvements"])


def test_star_structure_detected_for_behavioral():
    star = (
        "In my last project our team was migrating a payment service and the goal was zero downtime. I was "
        "responsible for the rollout plan. I built a canary release and wrote the rollback scripts. The result was "
        "a migration with no downtime and a 30% drop in incidents, and I learned to automate checks earlier."
    )
    vague = "I usually work hard with my team and things generally go well in most cases without many issues at all."
    s = agent.evaluate_answer(star, agent.STAR_POINTS, "behavioral")
    v = agent.evaluate_answer(vague, agent.STAR_POINTS, "behavioral")
    assert s["score"] > v["score"] + 20 and len(s["matched_points"]) >= 3


def test_keyword_matching_respects_word_boundaries():
    assert agent._kw_hit("we use aws daily", "aws")
    assert not agent._kw_hit("laws of physics", "aws")
    assert agent._kw_hit("reduced latency by 30%", "%")


def test_report_aggregates_and_requires_answers():
    qs = [
        {"category": "technical", "skill": "rag", "score": 90.0, "feedback": {"missing_points": []}},
        {"category": "technical", "skill": "aws", "score": 40.0, "feedback": {"missing_points": ["Security (IAM, secrets, VPC)"]}},
        {"category": "behavioral", "skill": None, "score": 70.0, "feedback": {"missing_points": ["Security (IAM, secrets, VPC)"]}},
        {"category": "behavioral", "skill": None, "score": None, "feedback": {}},
    ]
    r = agent.build_report(qs, ["kubernetes"])
    assert r["overall_score"] == 66.7 and r["answered"] == 3 and r["skipped"] == 1
    assert r["weak_skills"] == ["aws"] and r["strong_skills"] == ["rag"]
    assert r["top_improvement_themes"][0] == "Security (IAM, secrets, VPC)"
    assert r["readiness"] == "almost_ready"
    assert any("kubernetes" in s for s in r["next_steps"])
    with pytest.raises(ValueError):
        agent.build_report([{"category": "technical", "skill": None, "score": None, "feedback": {}}])


# ---------------------------------------------------------------------- API flow


@pytest.fixture()
def setup(client, tokens, db):
    t = tokens["access_token"]
    add_candidate(db)
    job = make_job(client, t, skills=["python", "rag", "fastapi", "aws"])
    return t, job


def start(client, t, **body):
    return client.post("/interviews/sessions", headers=auth(t), json=body)


def test_full_session_flow(client, setup):
    t, job = setup
    r = start(client, t, job_id=job["id"], num_questions=4)
    assert r.status_code == 201, r.text
    session = r.json()
    assert session["status"] == "IN_PROGRESS" and len(session["questions"]) == 4
    assert all("expected_points" not in q for q in session["questions"])  # rubric stays hidden
    assert [q["position"] for q in session["questions"]] == [1, 2, 3, 4]

    q = next(q for q in session["questions"] if q["skill"] == "rag") if any(
        q["skill"] == "rag" for q in session["questions"]) else session["questions"][0]
    a = client.post(f"/interviews/sessions/{session['id']}/questions/{q['id']}/answer", headers=auth(t),
                    json={"answer": GOOD_RAG_ANSWER})
    assert a.status_code == 200, a.text
    body = a.json()
    assert 0 <= body["score"] <= 100 and body["feedback"]["evaluator"] == "rule_based"
    assert body["feedback"]["improvements"] is not None and body["answered_at"]

    # report is gated until completion
    assert client.get(f"/interviews/sessions/{session['id']}/report", headers=auth(t)).status_code == 409

    done = client.post(f"/interviews/sessions/{session['id']}/complete", headers=auth(t))
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "COMPLETED" and done.json()["overall_score"] == body["score"]
    assert done.json()["summary"]["answered"] == 1 and done.json()["summary"]["skipped"] == 3

    report = client.get(f"/interviews/sessions/{session['id']}/report", headers=auth(t))
    assert report.status_code == 200 and report.json()["next_steps"]

    # completed sessions are frozen but completing again is idempotent
    again = client.post(f"/interviews/sessions/{session['id']}/questions/{q['id']}/answer", headers=auth(t),
                        json={"answer": "changed my mind"})
    assert again.status_code == 409
    assert client.post(f"/interviews/sessions/{session['id']}/complete", headers=auth(t)).status_code == 200

    listed = client.get("/interviews/sessions?status=completed", headers=auth(t)).json()
    assert len(listed) == 1 and listed[0]["overall_score"] == body["score"]


def test_answer_can_be_revised_before_completion(client, setup):
    t, job = setup
    s = start(client, t, job_id=job["id"], num_questions=3).json()
    qid = s["questions"][0]["id"]
    url = f"/interviews/sessions/{s['id']}/questions/{qid}/answer"
    low = client.post(url, headers=auth(t), json={"answer": "not sure"}).json()["score"]
    high = client.post(url, headers=auth(t), json={"answer": GOOD_RAG_ANSWER}).json()["score"]
    assert high > low
    assert client.get(f"/interviews/sessions/{s['id']}", headers=auth(t)).json()["questions"][0]["score"] == high


def test_complete_without_answers_is_rejected(client, setup):
    t, job = setup
    s = start(client, t, job_id=job["id"]).json()
    r = client.post(f"/interviews/sessions/{s['id']}/complete", headers=auth(t))
    assert r.status_code == 400 and "Answer at least one" in r.json()["detail"]


def test_start_from_application_links_session(client, setup):
    t, job = setup
    app = make_application(client, t, job["id"])
    s = start(client, t, application_id=app["id"], mode="behavioral", num_questions=3).json()
    assert s["application_id"] == app["id"] and s["job_id"] == job["id"]
    assert {q["category"] for q in s["questions"]} <= {"behavioral", "role_fit", "gap"}
    assert len(client.get(f"/interviews/sessions?application_id={app['id']}", headers=auth(t)).json()) == 1


def test_interview_practice_does_not_change_application_status(client, setup):
    t, job = setup
    app = make_application(client, t, job["id"])
    walk(client, t, app["id"], "PREPARED", "PENDING_APPROVAL")
    start(client, t, application_id=app["id"])
    assert client.get(f"/applications/{app['id']}", headers=auth(t)).json()["status"] == "PENDING_APPROVAL"


def test_second_session_for_same_job_avoids_repeats(client, setup):
    t, job = setup
    a = start(client, t, job_id=job["id"], num_questions=5).json()["questions"]
    b = start(client, t, job_id=job["id"], num_questions=5).json()["questions"]
    assert not {q["question"] for q in a} & {q["question"] for q in b}


def test_validation_and_not_found(client, setup):
    t, job = setup
    assert start(client, t).status_code == 422  # needs job_id or application_id
    assert start(client, t, job_id=job["id"], num_questions=1).status_code == 422
    assert start(client, t, job_id=job["id"], mode="chaos").status_code == 422
    missing = "00000000-0000-0000-0000-000000000000"
    assert start(client, t, job_id=missing).status_code == 404
    assert start(client, t, application_id=missing).status_code == 404
    s = start(client, t, job_id=job["id"]).json()
    qid = s["questions"][0]["id"]
    url = f"/interviews/sessions/{s['id']}/questions/{qid}/answer"
    assert client.post(url, headers=auth(t), json={"answer": ""}).status_code == 422
    assert client.post(url, headers=auth(t), json={"answer": "x" * 8001}).status_code == 422
    bad = f"/interviews/sessions/{s['id']}/questions/{missing}/answer"
    assert client.post(bad, headers=auth(t), json={"answer": "hello"}).status_code == 404


def test_sessions_are_private(client, setup):
    t, job = setup
    s = start(client, t, job_id=job["id"]).json()
    other = register_and_login(client, "other@example.com")["access_token"]
    assert client.get(f"/interviews/sessions/{s['id']}", headers=auth(other)).status_code == 404
    assert client.get("/interviews/sessions", headers=auth(other)).json() == []
    qid = s["questions"][0]["id"]
    assert client.post(f"/interviews/sessions/{s['id']}/questions/{qid}/answer", headers=auth(other),
                       json={"answer": "hi there friend"}).status_code == 404
    other_app = make_application(client, other, make_job(client, other, external_id="x")["id"])
    assert start(client, t, application_id=other_app["id"]).status_code == 404
    assert client.post("/interviews/sessions", json={"job_id": job["id"]}).status_code == 401


def test_works_without_candidate_profile(client, tokens):
    t = tokens["access_token"]
    job = make_job(client, t)
    r = start(client, t, job_id=job["id"])
    assert r.status_code == 201 and len(r.json()["questions"]) == 6


# --------------------------------------------------------------------- LLM paths


def _enable_llm(monkeypatch, reply):
    monkeypatch.setattr(llm, "is_configured", lambda: True)
    calls = []

    def fake(system, user, max_tokens=1800):
        calls.append(system)
        return reply(system) if callable(reply) else reply

    monkeypatch.setattr(llm, "complete_json", fake)
    return calls


def test_llm_questions_are_used_and_topped_up_from_templates(client, setup, monkeypatch):
    t, job = setup
    _enable_llm(monkeypatch, {"questions": [
        {"category": "technical", "skill": "rag", "question": "How would you shard a vector index across regions?",
         "expected_points": [{"label": "Sharding strategy", "keywords": ["shard", "partition"]}]},
        {"category": "nonsense", "question": "Dropped because the category is invalid", "expected_points": []},
        {"category": "technical", "question": "short", "expected_points": [{"label": "x", "keywords": ["x"]}]},
    ]})
    qs = start(client, t, job_id=job["id"], num_questions=4).json()["questions"]
    assert len(qs) == 4
    assert qs[0]["source"] == "llm" and "shard a vector index" in qs[0]["question"]
    assert {q["source"] for q in qs[1:]} == {"template"}


def test_llm_garbage_falls_back_to_templates(client, setup, monkeypatch):
    t, job = setup
    _enable_llm(monkeypatch, {"questions": "not a list"})
    qs = start(client, t, job_id=job["id"], num_questions=4).json()["questions"]
    assert len(qs) == 4 and {q["source"] for q in qs} == {"template"}


def test_llm_feedback_is_blended_with_rules(client, setup, monkeypatch):
    t, job = setup
    s = start(client, t, job_id=job["id"], num_questions=3).json()
    qid = s["questions"][0]["id"]
    url = f"/interviews/sessions/{s['id']}/questions/{qid}/answer"
    rule = client.post(url, headers=auth(t), json={"answer": GOOD_RAG_ANSWER}).json()["score"]
    _enable_llm(monkeypatch, {"score": 40, "strengths": ["Clear structure"], "improvements": ["Name a metric"]})
    blended = client.post(url, headers=auth(t), json={"answer": GOOD_RAG_ANSWER}).json()
    assert blended["feedback"]["evaluator"] == "rule_based+llm"
    assert blended["score"] == round((rule + 40) / 2, 1)
    assert "Clear structure" in blended["feedback"]["strengths"]


def test_llm_bad_feedback_is_ignored(client, setup, monkeypatch):
    t, job = setup
    s = start(client, t, job_id=job["id"], num_questions=3).json()
    qid = s["questions"][0]["id"]
    _enable_llm(monkeypatch, {"score": 9999, "strengths": [], "improvements": []})
    r = client.post(f"/interviews/sessions/{s['id']}/questions/{qid}/answer", headers=auth(t), json={"answer": GOOD_RAG_ANSWER})
    assert r.json()["feedback"]["evaluator"] == "rule_based"


# ---------------------------------------------------------------- llm client unit


def test_llm_unconfigured_returns_none(monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    try:
        assert llm.is_configured() is False
        assert llm.complete_json("s", "u") is None
    finally:
        get_settings.cache_clear()


def test_llm_json_extraction():
    assert llm._extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm._extract_json('Sure! {"a": 2} hope that helps') == {"a": 2}
    assert llm._extract_json("no json here") is None
    assert llm._extract_json("[1,2]") is None


def test_rate_limit_guard_for_llm_endpoints(client, setup, monkeypatch):
    t, job = setup
    from app.core.config import get_settings
    monkeypatch.setenv("LLM_RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    try:
        codes = [start(client, t, job_id=job["id"], num_questions=3).status_code for _ in range(3)]
    finally:
        get_settings.cache_clear()
    assert codes == [201, 201, 429]
