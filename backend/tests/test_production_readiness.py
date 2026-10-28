"""Phase 10: health probes, request pipeline, config guards and upload hardening."""

import io

import pytest
from sqlalchemy.exc import OperationalError

from app.core import database
from app.core.config import Settings
from tests.helpers import auth

PG = "postgresql+psycopg://u@db/app"


def prod(**kw):
    base = dict(environment="production", jwt_secret="x" * 40, database_url=PG)
    base.update(kw)
    return Settings(_env_file=None, **base)


# --------------------------------------------------------------------- config


def test_production_guards():
    prod().validate_for_runtime()
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        prod(database_url="sqlite:///./x.db").validate_for_runtime()
    with pytest.raises(RuntimeError, match="DEBUG"):
        prod(debug=True).validate_for_runtime()
    with pytest.raises(RuntimeError, match="CORS"):
        prod(cors_origins=["*"]).validate_for_runtime()


def test_development_is_not_restricted():
    Settings(_env_file=None, environment="development").validate_for_runtime()


def test_allowed_hosts_parses_from_env(monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", "api.example.com, localhost")
    assert Settings(_env_file=None).allowed_hosts == ["api.example.com", "localhost"]


# --------------------------------------------------------------------- probes


def test_liveness_and_version(client):
    assert client.get("/health").json() == {"status": "ok"}
    v = client.get("/version").json()
    assert v["environment"] == "test" and v["version"]


def test_readiness_ok(client):
    r = client.get("/health/ready")
    assert r.status_code == 200 and r.json() == {"status": "ready", "database": "ok"}


def test_readiness_reports_503_when_database_is_down(client, monkeypatch):
    class Broken:
        def connect(self):
            raise OperationalError("SELECT 1", {}, Exception("db down"))

    monkeypatch.setattr(database, "engine", Broken())
    r = client.get("/health/ready")
    assert r.status_code == 503 and r.json()["database"] == "down"
    assert client.get("/health").status_code == 200  # liveness unaffected


# ------------------------------------------------------------ request pipeline


def test_request_id_is_generated_and_echoed(client):
    generated = client.get("/health").headers["X-Request-ID"]
    assert len(generated) == 32
    assert client.get("/health", headers={"X-Request-ID": "trace-123"}).headers["X-Request-ID"] == "trace-123"
    assert len(client.get("/health", headers={"X-Request-ID": "x" * 200}).headers["X-Request-ID"]) == 64


def test_security_headers_present(client):
    h = client.get("/health").headers
    assert h["X-Content-Type-Options"] == "nosniff" and h["X-Frame-Options"] == "DENY"
    assert h["Cache-Control"] == "no-store"


def test_global_rate_limit_throttles_api_but_not_probes(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("API_RATE_LIMIT_PER_MINUTE", "3")
    get_settings.cache_clear()
    try:
        codes = [client.get("/jobs").status_code for _ in range(5)]  # 401s count toward the limit
        assert codes[:3] == [401, 401, 401] and codes[3:] == [429, 429]
        limited = client.get("/jobs")
        assert limited.headers["Retry-After"] and limited.headers["X-Request-ID"]
        assert client.get("/health").status_code == 200
        assert client.get("/health/ready").status_code == 200
    finally:
        get_settings.cache_clear()


def test_unhandled_errors_return_json_with_request_id(client):
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/_boom")
    def boom():
        raise RuntimeError("kaboom")

    client.app.include_router(router)
    r = client.get("/_boom", headers={"X-Request-ID": "abc"})
    assert r.status_code == 500
    assert r.json() == {"detail": "Internal server error", "request_id": "abc"}
    assert "kaboom" not in r.text


def test_docs_can_be_disabled(monkeypatch):
    from app.core.config import get_settings
    from app.main import create_app
    from fastapi.testclient import TestClient

    monkeypatch.setenv("DOCS_ENABLED", "false")
    get_settings.cache_clear()
    try:
        c = TestClient(create_app())
        assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404
    finally:
        get_settings.cache_clear()


# --------------------------------------------------------------------- uploads


def _pdf_bytes() -> bytes:
    from pypdf import PdfWriter

    buf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.write(buf)
    return buf.getvalue()


@pytest.fixture()
def upload_dir(tmp_path, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "up"))
    get_settings.cache_clear()
    yield tmp_path / "up"
    get_settings.cache_clear()


def test_upload_sanitises_client_filename(client, tokens, upload_dir, monkeypatch):
    monkeypatch.setattr("app.api.resumes.parse_resume", lambda b, t: "parsed text")
    r = client.post(
        "/resumes/upload", headers=auth(tokens["access_token"]),
        files={"file": ("../../etc/pass wd?.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    saved = list(upload_dir.iterdir())
    assert len(saved) == 1 and saved[0].parent == upload_dir  # stayed inside the upload dir
    assert ".." not in saved[0].name and "?" not in saved[0].name and " " not in saved[0].name


def test_upload_same_filename_twice_keeps_both_files(client, tokens, upload_dir, monkeypatch):
    monkeypatch.setattr("app.api.resumes.parse_resume", lambda b, t: "parsed text")
    for _ in range(2):
        client.post("/resumes/upload", headers=auth(tokens["access_token"]),
                    files={"file": ("cv.pdf", _pdf_bytes(), "application/pdf")})
    assert len(list(upload_dir.iterdir())) == 2


def test_upload_size_limit(client, tokens, upload_dir, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()
    r = client.post("/resumes/upload", headers=auth(tokens["access_token"]),
                    files={"file": ("big.pdf", b"0" * (1024 * 1024 + 1), "application/pdf")})
    assert r.status_code == 413
    assert not upload_dir.exists() or not list(upload_dir.iterdir())


def test_upload_rejects_other_extensions_and_hides_parser_errors(client, tokens, upload_dir):
    t = tokens["access_token"]
    assert client.post("/resumes/upload", headers=auth(t),
                       files={"file": ("a.exe", b"x", "application/octet-stream")}).status_code == 400
    r = client.post("/resumes/upload", headers=auth(t), files={"file": ("a.pdf", b"not a pdf", "application/pdf")})
    assert r.status_code == 400 and "Traceback" not in r.text and "valid PDF" in r.json()["detail"]
