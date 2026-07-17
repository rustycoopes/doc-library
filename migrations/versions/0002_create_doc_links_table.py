"""Create doc_library.doc_links

Revision ID: 0002_create_doc_links_table
Revises: 0001_create_doc_library_schema
Create Date: 2026-07-17

The feature's core entity (Slice 3): a single user-saved link with title/url/category. No
sort_order column - ordering is computed at query time (ORDER BY category, title), never stored.
FK to host.users.id relies on the REFERENCES-only grant 0001 already gave doc_library_app.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_create_doc_links_table"
down_revision: str | None = "0001_create_doc_library_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "doc_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"], ["host.users.id"], ondelete="cascade", name="fk_doc_links_user_id"
        ),
        schema="doc_library",
    )
    op.create_index(
        "ix_doc_links_user_id", "doc_links", ["user_id"], schema="doc_library"
    )


def downgrade() -> None:
    op.drop_index("ix_doc_links_user_id", table_name="doc_links", schema="doc_library")
    op.drop_table("doc_links", schema="doc_library")
