"""phase 8: follow-up completion tracking + fix schema drift found when running on PostgreSQL

Revision ID: a8b1c2d3e4f5
Revises: f1f2_phase5_8
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a8b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "f1f2_phase5_8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    with op.batch_alter_table("follow_ups") as batch_op:
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    # The phase 5-8 migration never created these indexes that the models declare.
    with op.batch_alter_table("application_events") as batch_op:
        batch_op.create_index("ix_application_events_to_status", ["to_status"], unique=False)

    with op.batch_alter_table("documents") as batch_op:
        batch_op.create_index("ix_documents_source_id", ["source_id"], unique=False)

    # application_packages.application_id is unique in the model; the index was created non-unique.
    with op.batch_alter_table("application_packages") as batch_op:
        batch_op.drop_index("ix_application_packages_application_id")
        batch_op.create_index("ix_application_packages_application_id", ["application_id"], unique=True)

    if _is_postgres():
        # candidate_intelligence timestamps were created without a time zone; the model is tz-aware.
        # Existing values were written as UTC.
        for column in ("created_at", "updated_at"):
            op.alter_column(
                "candidate_intelligence", column,
                existing_type=sa.DateTime(), type_=sa.DateTime(timezone=True),
                existing_nullable=False, postgresql_using=f"{column} AT TIME ZONE 'UTC'",
            )
        # These tables carry both a UNIQUE constraint and a unique index on the same column.
        # The model declares only the index, so drop the redundant constraint.
        inspector = sa.inspect(op.get_bind())
        for table, column in (("candidate_intelligence", "user_id"), ("application_packages", "application_id")):
            for constraint in inspector.get_unique_constraints(table):
                if constraint["column_names"] == [column]:
                    op.drop_constraint(constraint["name"], table, type_="unique")


def downgrade() -> None:
    if _is_postgres():
        for column in ("created_at", "updated_at"):
            op.alter_column(
                "candidate_intelligence", column,
                existing_type=sa.DateTime(timezone=True), type_=sa.DateTime(),
                existing_nullable=False, postgresql_using=f"{column} AT TIME ZONE 'UTC'",
            )

    with op.batch_alter_table("application_packages") as batch_op:
        batch_op.drop_index("ix_application_packages_application_id")
        batch_op.create_index("ix_application_packages_application_id", ["application_id"], unique=False)

    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_index("ix_documents_source_id")

    with op.batch_alter_table("application_events") as batch_op:
        batch_op.drop_index("ix_application_events_to_status")

    with op.batch_alter_table("follow_ups") as batch_op:
        batch_op.drop_column("completed_at")
