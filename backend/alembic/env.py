from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from app import models  # noqa: F401  (registers all tables on Base.metadata)
from app.core.config import get_settings
from app.core.database import Base, make_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _url() -> str:
    # DATABASE_URL from the environment/.env is the single source of truth.
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_url().startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Tests (and programmatic callers) can hand us an open connection.
    existing = config.attributes.get("connection")
    if existing is not None:
        _run(existing)
        return
    with make_engine(_url()).connect() as connection:
        _run(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
