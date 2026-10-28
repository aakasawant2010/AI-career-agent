"""phase 9: interview agent (sessions and questions)

Revision ID: b9c2d3e4f5a6
Revises: a8b1c2d3e4f5
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b9c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a8b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interview_sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=True),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("interview_sessions") as batch_op:
        batch_op.create_index("ix_interview_sessions_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_interview_sessions_job_id", ["job_id"], unique=False)
        batch_op.create_index("ix_interview_sessions_application_id", ["application_id"], unique=False)
        batch_op.create_index("ix_interview_sessions_status", ["status"], unique=False)

    op.create_table(
        "interview_questions",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("skill", sa.String(length=100), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_points", sa.JSON(), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("feedback", sa.JSON(), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "position", name="uq_interview_questions_session_position"),
    )
    with op.batch_alter_table("interview_questions") as batch_op:
        batch_op.create_index("ix_interview_questions_session_id", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_table("interview_questions")
    op.drop_table("interview_sessions")
