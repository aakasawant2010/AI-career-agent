"""The Alembic migrations must produce exactly the schema the models declare."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool

from app.core.database import Base


def _migrated_engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    cfg = Config("alembic.ini")
    with eng.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
    return eng


def test_upgrade_creates_expected_tables():
    eng = _migrated_engine()
    assert {"users", "refresh_tokens", "audit_logs"} <= set(inspect(eng).get_table_names())


def test_migrations_match_models():
    eng = _migrated_engine()
    with eng.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == [], f"models and migrations have drifted: {diff}"


def test_single_migration_head():
    """Two heads means two branches were merged badly and `alembic upgrade head` would fail."""
    from alembic.script import ScriptDirectory

    heads = ScriptDirectory.from_config(Config("alembic.ini")).get_heads()
    assert len(heads) == 1, f"multiple alembic heads: {heads}"


def test_downgrade_to_base_removes_everything():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    cfg = Config("alembic.ini")
    with eng.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")
    assert set(inspect(eng).get_table_names()) <= {"alembic_version"}


def test_phase_8_and_9_tables_exist():
    tables = set(inspect(_migrated_engine()).get_table_names())
    assert {"applications", "follow_ups", "interview_sessions", "interview_questions"} <= tables
