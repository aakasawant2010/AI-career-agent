from datetime import timedelta

import jwt
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import utcnow
from app.core.rate_limit import limiter
from app.core.security import hash_refresh_token
from app.models import AuditLog, RefreshToken, User


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------- registration ----------


def test_register_success_hides_password(client):
    r = client.post(
        "/auth/register",
        json={"email": "New@Example.com", "password": "abcd1234!", "full_name": " Lex "},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "new@example.com"  # normalised to lower case
    assert data["full_name"] == "Lex"
    assert "password" not in data and "password_hash" not in data


def test_register_stores_hash_not_plaintext(client, db):
    client.post("/auth/register", json={"email": "a@b.co", "password": "abcd1234!"})
    user = db.scalar(select(User).where(User.email == "a@b.co"))
    assert user.password_hash != "abcd1234!"
    assert user.password_hash.startswith("$2")  # bcrypt


def test_register_duplicate_email_conflicts_case_insensitively(client, registered):
    r = client.post(
        "/auth/register", json={"email": "LEX@example.com", "password": "another-pass1"}
    )
    assert r.status_code == 409


def test_register_rejects_weak_or_invalid_input(client):
    assert client.post("/auth/register", json={"email": "x@y.co", "password": "short1"}).status_code == 422
    assert client.post("/auth/register", json={"email": "x@y.co", "password": "onlyletters"}).status_code == 422
    assert client.post("/auth/register", json={"email": "not-an-email", "password": "abcd1234!"}).status_code == 422
    too_long = "a1" * 40
    assert client.post("/auth/register", json={"email": "x@y.co", "password": too_long}).status_code == 422


# ---------- login ----------


def test_login_success_returns_token_pair(client, registered):
    r = client.post(
        "/auth/login", json={"email": registered["email"], "password": registered["password"]}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"] and data["refresh_token"]


def test_login_wrong_password_and_unknown_email_look_identical(client, registered):
    bad_pw = client.post("/auth/login", json={"email": registered["email"], "password": "wrong-pass1"})
    unknown = client.post("/auth/login", json={"email": "ghost@example.com", "password": "wrong-pass1"})
    assert bad_pw.status_code == unknown.status_code == 401
    assert bad_pw.json() == unknown.json()


def test_login_failures_are_audited(client, registered, db):
    client.post("/auth/login", json={"email": registered["email"], "password": "wrong-pass1"})
    actions = [a.action for a in db.scalars(select(AuditLog))]
    assert "auth.login_failed" in actions


# ---------- protected routes ----------


def test_me_requires_valid_token(client, tokens):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers=auth("garbage")).status_code == 401
    r = client.get("/auth/me", headers=auth(tokens["access_token"]))
    assert r.status_code == 200
    assert r.json()["email"] == "lex@example.com"


def test_expired_access_token_rejected(client, registered, db):
    user = db.scalar(select(User))
    s = get_settings()
    expired = jwt.encode(
        {"sub": str(user.id), "type": "access", "exp": utcnow() - timedelta(minutes=1)},
        s.jwt_secret,
        algorithm=s.jwt_algorithm,
    )
    assert client.get("/auth/me", headers=auth(expired)).status_code == 401


def test_token_signed_with_wrong_secret_rejected(client, registered, db):
    user = db.scalar(select(User))
    forged = jwt.encode(
        {"sub": str(user.id), "type": "access", "exp": utcnow() + timedelta(minutes=5)},
        "some-other-secret-some-other-secret-0",
        algorithm="HS256",
    )
    assert client.get("/auth/me", headers=auth(forged)).status_code == 401


def test_refresh_token_cannot_be_used_as_access_token(client, tokens):
    assert client.get("/auth/me", headers=auth(tokens["refresh_token"])).status_code == 401


def test_deactivated_user_loses_access(client, tokens, db):
    user = db.scalar(select(User))
    user.is_active = False
    db.commit()
    assert client.get("/auth/me", headers=auth(tokens["access_token"])).status_code == 401


# ---------- refresh rotation ----------


def test_refresh_rotates_token(client, tokens):
    r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    new = r.json()
    assert new["refresh_token"] != tokens["refresh_token"]
    assert client.get("/auth/me", headers=auth(new["access_token"])).status_code == 200


def test_refresh_token_reuse_revokes_whole_family(client, tokens):
    first = tokens["refresh_token"]
    second = client.post("/auth/refresh", json={"refresh_token": first}).json()["refresh_token"]
    # Replaying the already-rotated token is treated as theft...
    assert client.post("/auth/refresh", json={"refresh_token": first}).status_code == 401
    # ...so even the legitimately-issued newer token is now dead.
    assert client.post("/auth/refresh", json={"refresh_token": second}).status_code == 401


def test_refresh_with_unknown_token_rejected(client, registered):
    r = client.post("/auth/refresh", json={"refresh_token": "x" * 40})
    assert r.status_code == 401


def test_expired_refresh_token_rejected(client, tokens, db):
    row = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(tokens["refresh_token"]))
    )
    row.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_refresh_tokens_stored_hashed(client, tokens, db):
    raw = tokens["refresh_token"]
    stored = [r.token_hash for r in db.scalars(select(RefreshToken))]
    assert raw not in stored
    assert hash_refresh_token(raw) in stored


# ---------- logout ----------


def test_logout_revokes_refresh_token(client, tokens):
    assert client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_logout_with_unknown_token_is_idempotent(client):
    assert client.post("/auth/logout", json={"refresh_token": "x" * 40}).status_code == 204


# ---------- rate limiting & misc ----------


def test_login_is_rate_limited(client, registered):
    limiter.reset()
    limit = get_settings().auth_rate_limit_attempts
    codes = [
        client.post("/auth/login", json={"email": registered["email"], "password": "wrong-pass1"}).status_code
        for _ in range(limit + 2)
    ]
    assert codes[:limit] == [401] * limit
    assert codes[limit:] == [429, 429]
    blocked = client.post("/auth/login", json={"email": registered["email"], "password": "wrong-pass1"})
    assert int(blocked.headers["Retry-After"]) >= 1


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_production_refuses_weak_jwt_secret(monkeypatch):
    import pytest

    from app.core.config import Settings

    with pytest.raises(RuntimeError):
        Settings(environment="production", jwt_secret="change-me-in-env").validate_for_runtime()
    with pytest.raises(RuntimeError):
        Settings(environment="production", jwt_secret="short").validate_for_runtime()
    Settings(
        environment="production", jwt_secret="x" * 40, database_url="postgresql+psycopg://u@db/app"
    ).validate_for_runtime()  # ok
