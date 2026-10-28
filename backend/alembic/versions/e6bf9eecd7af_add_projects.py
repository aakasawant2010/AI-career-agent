"""add projects

Revision ID: e6bf9eecd7af
Revises: 84dc1122feff
Create Date: 2026-10-21 22:44:14.251281

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6bf9eecd7af"
down_revision: Union[str, Sequence[str], None] = "84dc1122feff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "projects",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("technologies", sa.JSON(), nullable=False),
        sa.Column("github_url", sa.String(length=500), nullable=True),
        sa.Column("live_url", sa.String(length=500), nullable=True),
        sa.Column("role", sa.String(length=200), nullable=True),
        sa.Column("featured", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_projects_user_id"),
            ["user_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("projects")