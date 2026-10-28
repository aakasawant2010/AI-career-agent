"""add candidate intelligence

Revision ID: ba74851bf6a6
Revises: 413cdf7d196a
Create Date: 2026-10-22 15:02:08.114776

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ba74851bf6a6"
down_revision: Union[str, Sequence[str], None] = "413cdf7d196a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "candidate_intelligence",
        sa.Column(
            "user_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "career_profile",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "resume_intelligence",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "projects",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "core_skills",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "technologies",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "target_roles",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "preferred_locations",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "professional_summary",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_index(
        "ix_candidate_intelligence_user_id",
        "candidate_intelligence",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_candidate_intelligence_user_id", table_name="candidate_intelligence")
    op.drop_table("candidate_intelligence")
