"""Phase 8: status pipeline, follow-up reminders and analytics."""

from datetime import datetime, timedelta, timezone

from tests.helpers import (
    TO_SUBMITTED, auth, backdate, make_application, make_job, register_and_login, set_status, walk,
)


def new_app(client, token, external_id="job-1", **job_overrides):
    job = make_job(client, token, external_id=external_id, **job_overrides)
    return make_application(client, token, job["id"]), job


def submitted_app(client, token, external_id="job-1", **job_overrides):
    app, job = new_app(client, token, external_id, **job_overrides)
    walk(client, token, app["id"], *TO_SUBMITTED)
    return app, job


# ---------------------------------------------------------------- status pipeline


def test_full_pipeline_to_accepted(client, tokens):
    t = tokens["access_token"]
    app, _ = submitted_app(client, t)
    walk(client, t, app["id"], "SCREENING", "INTERVIEW", "OFFER", "ACCEPTED")
    assert client.get(f"/applications/{app['id']}", headers=auth(t)).json()["status"] == "ACCEPTED"
    events = client.get(f"/applications/{app['id']}/events", headers=auth(t))
    assert events.status_code == 200
    assert [e["to_status"] for e in events.json()][-4:] == ["SCREENING", "INTERVIEW", "OFFER", "ACCEPTED"]


def test_screening_can_be_skipped(client, tokens):
    t = tokens["access_token"]
    app, _ = submitted_app(client, t)
    set_status(client, t, app["id"], "INTERVIEW")


def test_invalid_transitions_rejected(client, tokens):
    t = tokens["access_token"]
    app, _ = new_app(client, t)
    set_status(client, t, app["id"], "INTERVIEW", expect=409)  # cannot skip submission
    walk(client, t, app["id"], *TO_SUBMITTED)
    set_status(client, t, app["id"], "OFFER", expect=409)  # cannot skip interviews
    set_status(client, t, app["id"], "ACCEPTED", expect=409)
    set_status(client, t, app["id"], "NOT_A_STATUS", expect=409)


def test_terminal_states_are_final(client, tokens):
    t = tokens["access_token"]
    app, _ = submitted_app(client, t)
    set_status(client, t, app["id"], "REJECTED")
    set_status(client, t, app["id"], "INTERVIEW", expect=409)


# -------------------------------------------------------------------- follow-ups


def test_submission_schedules_follow_up_and_rejection_cancels_it(client, tokens):
    t = tokens["access_token"]
    app, _ = submitted_app(client, t)
    items = client.get(f"/applications/{app['id']}/follow-ups", headers=auth(t)).json()
    assert len(items) == 1 and items[0]["status"] == "PENDING"
    due = datetime.fromisoformat(items[0]["due_at"].replace("Z", "+00:00"))
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    assert timedelta(days=6) < due - datetime.now(timezone.utc) < timedelta(days=8)

    set_status(client, t, app["id"], "REJECTED")
    items = client.get(f"/applications/{app['id']}/follow-ups", headers=auth(t)).json()
    assert items[0]["status"] == "CANCELLED"


def test_follow_up_complete_reschedule_and_guards(client, tokens):
    t = tokens["access_token"]
    app, _ = submitted_app(client, t)
    fid = client.get(f"/follow-ups", headers=auth(t)).json()[0]["id"]

    new_due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    r = client.patch(f"/follow-ups/{fid}", headers=auth(t), json={"due_at": new_due, "note": "ping recruiter"})
    assert r.status_code == 200 and r.json()["note"] == "ping recruiter"

    r = client.patch(f"/follow-ups/{fid}", headers=auth(t), json={"status": "DONE"})
    assert r.status_code == 200 and r.json()["status"] == "DONE" and r.json()["completed_at"]

    # a finished reminder can't be reopened or rescheduled
    assert client.patch(f"/follow-ups/{fid}", headers=auth(t), json={"status": "PENDING"}).status_code == 409
    assert client.patch(f"/follow-ups/{fid}", headers=auth(t), json={"due_at": new_due}).status_code == 409
    assert client.patch(f"/follow-ups/{fid}", headers=auth(t), json={"status": "BOGUS"}).status_code == 409


def test_follow_up_inbox_flags_overdue_and_filters(client, tokens):
    t = tokens["access_token"]
    app, _ = submitted_app(client, t)
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    r = client.post(f"/applications/{app['id']}/follow-ups", headers=auth(t), json={"due_at": past, "note": "late"})
    assert r.status_code == 200
    items = client.get("/follow-ups", headers=auth(t)).json()
    assert items[0]["note"] == "late" and items[0]["overdue"] is True  # soonest-due first
    assert any(not i["overdue"] for i in items)
    soon = client.get("/follow-ups?due_within_days=1", headers=auth(t)).json()
    assert [i["note"] for i in soon] == ["late"]
    assert client.get("/follow-ups?status=DONE", headers=auth(t)).json() == []


def test_follow_ups_are_private_to_their_owner(client, tokens):
    t = tokens["access_token"]
    app, _ = submitted_app(client, t)
    fid = client.get("/follow-ups", headers=auth(t)).json()[0]["id"]
    other = register_and_login(client, "other@example.com")["access_token"]
    assert client.get("/follow-ups", headers=auth(other)).json() == []
    assert client.patch(f"/follow-ups/{fid}", headers=auth(other), json={"status": "DONE"}).status_code == 404
    assert client.get(f"/applications/{app['id']}/follow-ups", headers=auth(other)).status_code == 404


# --------------------------------------------------------------------- analytics


def build_pipeline(client, t, db):
    """A: reached OFFER · B: rejected after screening · C: awaiting · D: never submitted."""
    a, _ = submitted_app(client, t, "a", title="AI Engineer", company="Alpha", source="linkedin")
    walk(client, t, a["id"], "SCREENING", "INTERVIEW", "OFFER")
    b, _ = submitted_app(client, t, "b", title="ML Engineer", company="Beta", source="linkedin")
    walk(client, t, b["id"], "SCREENING", "REJECTED")
    c, _ = submitted_app(client, t, "c", title="AI Engineer", company="Gamma", source="naukri")
    d, _ = new_app(client, t, "d", company="Delta", source="naukri")
    backdate(db, a["id"], submitted_days_ago=20, event_days_ago={"SCREENING": 15})
    backdate(db, b["id"], submitted_days_ago=10, event_days_ago={"SCREENING": 6, "REJECTED": 4})
    backdate(db, c["id"], submitted_days_ago=3)
    return a, b, c, d


def test_funnel_counts_stages_reached_not_just_current_status(client, tokens, db):
    t = tokens["access_token"]
    build_pipeline(client, t, db)
    funnel = client.get("/analytics/funnel", headers=auth(t)).json()
    counts = {s["stage"]: s["count"] for s in funnel["stages"]}
    assert counts == {"CREATED": 4, "SUBMITTED": 3, "SCREENING": 2, "INTERVIEW": 1, "OFFER": 1, "ACCEPTED": 0}
    by_stage = {s["stage"]: s for s in funnel["stages"]}
    assert by_stage["SCREENING"]["conversion_from_previous"] == 66.7
    assert by_stage["OFFER"]["conversion_from_submitted"] == 33.3
    assert funnel["rejected"] == 1 and funnel["active"] == 3


def test_response_rate_and_time_to_response(client, tokens, db):
    t = tokens["access_token"]
    build_pipeline(client, t, db)
    r = client.get("/analytics/response", headers=auth(t)).json()
    assert r["submitted"] == 3 and r["responded"] == 2
    assert r["response_rate"] == 66.7 and r["positive_response_rate"] == 66.7
    # A responded after 5 days (20-15), B after 4 days (10-6)
    assert r["avg_days_to_response"] == 4.5 and r["median_days_to_response"] == 4.5
    assert r["awaiting_response"] == 1 and r["ghosted"] == 0


def test_ghosted_after_threshold(client, tokens, db):
    t = tokens["access_token"]
    app, _ = submitted_app(client, t)
    backdate(db, app["id"], submitted_days_ago=45)
    assert client.get("/analytics/response", headers=auth(t)).json()["ghosted"] == 1


def test_rejection_before_submission_is_not_a_response(client, tokens):
    t = tokens["access_token"]
    app, _ = new_app(client, t)
    set_status(client, t, app["id"], "REJECTED")
    r = client.get("/analytics/response", headers=auth(t)).json()
    assert r["submitted"] == 0 and r["responded"] == 0 and r["response_rate"] == 0


def test_breakdown_by_source_company_and_validation(client, tokens, db):
    t = tokens["access_token"]
    build_pipeline(client, t, db)
    rows = client.get("/analytics/breakdown?by=source", headers=auth(t)).json()
    by_key = {r["key"]: r for r in rows}
    assert by_key["linkedin"]["applications"] == 2 and by_key["linkedin"]["responses"] == 2
    assert by_key["linkedin"]["interviews"] == 1 and by_key["linkedin"]["interview_rate"] == 50.0
    assert by_key["naukri"]["applications"] == 2 and by_key["naukri"]["submitted"] == 1
    assert by_key["naukri"]["responses"] == 0
    roles = {r["key"] for r in client.get("/analytics/breakdown?by=role", headers=auth(t)).json()}
    assert roles == {"AI Engineer", "ML Engineer", "Generative AI Engineer"}
    assert client.get("/analytics/breakdown?by=nonsense", headers=auth(t)).status_code == 422
    assert client.get("/analytics/breakdown?by=match_band", headers=auth(t)).json()[0]["key"] == "unscored"


def test_timeline_has_one_bucket_per_week(client, tokens, db):
    t = tokens["access_token"]
    build_pipeline(client, t, db)
    points = client.get("/analytics/timeline?weeks=6", headers=auth(t)).json()
    assert len(points) == 6
    assert sum(p["created"] for p in points) == 4
    assert sum(p["submitted"] for p in points) == 3
    assert sum(p["responses"] for p in points) == 2


def test_overview_needs_attention(client, tokens, db):
    t = tokens["access_token"]
    build_pipeline(client, t, db)
    app, _ = new_app(client, t, "e")
    walk(client, t, app["id"], "PREPARED", "PENDING_APPROVAL")
    o = client.get("/analytics/overview", headers=auth(t)).json()
    assert o["total_applications"] == 5
    assert o["needs_attention"]["awaiting_your_approval"] == 1
    assert o["funnel"]["stages"][0]["count"] == 5
    assert o["by_status"]["OFFER"] == 1 and o["follow_ups"]["open"] == 2  # A,C open; B cancelled


def test_analytics_are_scoped_to_the_user_and_empty_state_is_safe(client, tokens, db):
    t = tokens["access_token"]
    build_pipeline(client, t, db)
    other = register_and_login(client, "other@example.com")["access_token"]
    o = client.get("/analytics/overview", headers=auth(other)).json()
    assert o["total_applications"] == 0 and o["response"]["response_rate"] == 0
    assert o["response"]["avg_days_to_response"] is None
    assert client.get("/analytics/funnel", headers=auth(other)).json()["stages"][0]["count"] == 0


def test_analytics_require_auth(client):
    for path in ("/analytics/overview", "/analytics/funnel", "/follow-ups"):
        assert client.get(path).status_code == 401


def test_legacy_summary_still_works_on_any_backend(client, tokens):
    t = tokens["access_token"]
    new_app(client, t)
    r = client.get("/applications/analytics/summary", headers=auth(t))
    assert r.status_code == 200 and r.json()["applications_last_30_days"] == 1
