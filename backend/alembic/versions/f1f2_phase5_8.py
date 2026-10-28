"""phase 5-8 rag applications approval tracking analytics"""
from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union
revision="f1f2_phase5_8"; down_revision="c9d2e7f1a111"; branch_labels=None; depends_on=None
def upgrade():
    op.create_table("documents",
        sa.Column("user_id",sa.Uuid(),nullable=False), sa.Column("kind",sa.String(50),nullable=False),
        sa.Column("source_id",sa.String(100)), sa.Column("title",sa.String(300),nullable=False),
        sa.Column("content",sa.Text(),nullable=False), sa.Column("metadata",sa.JSON(),nullable=False),
        sa.Column("content_hash",sa.String(64),nullable=False), sa.Column("id",sa.Uuid(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False), sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(["user_id"],["users.id"],ondelete="CASCADE"),sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_documents_user_id","documents",["user_id"]);op.create_index("ix_documents_kind","documents",["kind"]);op.create_index("ix_documents_content_hash","documents",["content_hash"])
    op.create_table("document_chunks",
        sa.Column("document_id",sa.Uuid(),nullable=False),sa.Column("chunk_index",sa.Integer(),nullable=False),
        sa.Column("content",sa.Text(),nullable=False),sa.Column("embedding",sa.JSON(),nullable=False),sa.Column("metadata",sa.JSON(),nullable=False),
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(["document_id"],["documents.id"],ondelete="CASCADE"),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("document_id","chunk_index",name="uq_document_chunks_document_index"))
    op.create_index("ix_document_chunks_document_id","document_chunks",["document_id"])
    op.create_table("applications",
        sa.Column("user_id",sa.Uuid(),nullable=False),sa.Column("job_id",sa.Uuid(),nullable=False),sa.Column("status",sa.String(50),nullable=False),
        sa.Column("submission_mode",sa.String(50),nullable=False),sa.Column("notes",sa.Text()),sa.Column("submitted_at",sa.DateTime(timezone=True)),
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(["user_id"],["users.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["job_id"],["jobs.id"],ondelete="CASCADE"),sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_applications_user_id","applications",["user_id"]);op.create_index("ix_applications_job_id","applications",["job_id"]);op.create_index("ix_applications_status","applications",["status"])
    op.create_table("application_packages",
        sa.Column("application_id",sa.Uuid(),nullable=False),sa.Column("resume_id",sa.Uuid()),sa.Column("resume_content",sa.Text()),
        sa.Column("cover_letter",sa.Text()),sa.Column("answers",sa.JSON(),nullable=False),sa.Column("grounding_issues",sa.JSON(),nullable=False),
        sa.Column("readiness",sa.String(50),nullable=False),sa.Column("id",sa.Uuid(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(["application_id"],["applications.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["resume_id"],["resumes.id"],ondelete="SET NULL"),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("application_id"))
    op.create_index("ix_application_packages_application_id","application_packages",["application_id"])
    op.create_table("application_events",
        sa.Column("application_id",sa.Uuid(),nullable=False),sa.Column("from_status",sa.String(50)),sa.Column("to_status",sa.String(50),nullable=False),
        sa.Column("actor",sa.String(50),nullable=False),sa.Column("note",sa.Text()),sa.Column("id",sa.Uuid(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(["application_id"],["applications.id"],ondelete="CASCADE"),sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_application_events_application_id","application_events",["application_id"])
    op.create_table("follow_ups",
        sa.Column("application_id",sa.Uuid(),nullable=False),sa.Column("due_at",sa.DateTime(timezone=True),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("note",sa.Text()),
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(["application_id"],["applications.id"],ondelete="CASCADE"),sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_follow_ups_application_id","follow_ups",["application_id"]);op.create_index("ix_follow_ups_status","follow_ups",["status"])
def downgrade():
    op.drop_table("follow_ups");op.drop_table("application_events");op.drop_table("application_packages");op.drop_table("applications");op.drop_table("document_chunks");op.drop_table("documents")
