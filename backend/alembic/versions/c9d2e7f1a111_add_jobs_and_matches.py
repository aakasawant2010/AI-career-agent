"""add jobs and job matches

Revision ID: c9d2e7f1a111
Revises: ba74851bf6a6
Create Date: 2026-10-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c9d2e7f1a111"
down_revision: Union[str, Sequence[str], None] = "ba74851bf6a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=300), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("company", sa.String(length=300), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("work_mode", sa.String(length=50), nullable=False),
        sa.Column("employment_type", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("technologies", sa.JSON(), nullable=False),
        sa.Column("min_salary_lpa", sa.Float(), nullable=True),
        sa.Column("max_salary_lpa", sa.Float(), nullable=True),
        sa.Column("salary_text", sa.String(length=500), nullable=True),
        sa.Column("experience_min_years", sa.Float(), nullable=True),
        sa.Column("experience_max_years", sa.Float(), nullable=True),
        sa.Column("notice_period_days", sa.Integer(), nullable=True),
        sa.Column("apply_url", sa.String(length=1000), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("job_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_hash", name="uq_jobs_job_hash"),
    )
    with op.batch_alter_table("jobs") as batch_op:
        for name, cols in [
            ("ix_jobs_source", ["source"]),
            ("ix_jobs_external_id", ["external_id"]),
            ("ix_jobs_title", ["title"]),
            ("ix_jobs_company", ["company"]),
            ("ix_jobs_location", ["location"]),
            ("ix_jobs_work_mode", ["work_mode"]),
            ("ix_jobs_job_hash", ["job_hash"]),
            ("ix_jobs_is_active", ["is_active"]),
        ]:
            batch_op.create_index(name, cols, unique=False)

    op.create_table(
        "job_matches",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("recommendation", sa.String(length=50), nullable=False),
        sa.Column("breakdown", sa.JSON(), nullable=False),
        sa.Column("matched_skills", sa.JSON(), nullable=False),
        sa.Column("missing_skills", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_job_matches_user_job"),
    )
    with op.batch_alter_table("job_matches") as batch_op:
        batch_op.create_index("ix_job_matches_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_job_matches_job_id", ["job_id"], unique=False)
        batch_op.create_index("ix_job_matches_score", ["score"], unique=False)
        batch_op.create_index("ix_job_matches_recommendation", ["recommendation"], unique=False)


def downgrade() -> None:
    op.drop_table("job_matches")
    op.drop_table("jobs")
