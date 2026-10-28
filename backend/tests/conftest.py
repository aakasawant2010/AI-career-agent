import os

os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-123"
os.environ["DATABASE_URL"] = "sqlite://"

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db, make_engine
from app.core.rate_limit import limiter
from app.main import create_app


@pytest.fixture()
def engine():
    """In-memory SQLite by default. Set TEST_DATABASE_URL to run the suite on Postgres
    (the target database), e.g. postgresql+psycopg://user@host:5432/testdb. Tables are
    created and dropped around every test, so point it at a throwaway database."""
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        eng = make_engine(url)
        Base.metadata.drop_all(eng)
    else:
        from sqlalchemy import create_engine

        # In-memory SQLite needs one shared connection across threads.
        eng = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

        @event.listens_for(eng, "connect")
        def _fk_on(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    yield eng
    if url:
        Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def db(engine) -> Iterator[Session]:
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(engine) -> Iterator[TestClient]:
    limiter.reset()
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _get_db() -> Iterator[Session]:
        s = factory()
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def registered(client):
    body = {"email": "lex@example.com", "password": "s3cret-pass1", "full_name": "Lex"}
    assert client.post("/auth/register", json=body).status_code == 201
    return body


@pytest.fixture()
def tokens(client, registered) -> dict:
    r = client.post(
        "/auth/login", json={"email": registered["email"], "password": registered["password"]}
    )
    assert r.status_code == 200
    return r.json()
