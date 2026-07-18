"""Create doc_library.user_preferences

Revision ID: 0003_create_user_preferences_table
Revises: 0002_create_doc_links_table
Create Date: 2026-07-17

Slice 4: a lazily-created singleton-per-user row holding view_mode. No row is created here or at
registration - get_view_mode() defaults to "list" when the row doesn't exist, and a row is only
ever written by set_view_mode() on a user's first PUT. FK to host.users.id relies on the same
REFERENCES-only grant 0001 gave doc_library_app.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_create_user_preferences_table"
down_revision: str | None = "0002_create_doc_links_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.Uuid(), primary_key=True),
        sa.Column("view_mode", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["host.users.id"],
            ondelete="cascade",
            name="fk_user_preferences_user_id",
        ),
        # Defense-in-depth: the Pydantic Literal["list", "tiles"] schema is the primary guard on
        # every route path, but a direct-SQL/maintenance script bypassing it should still be
        # unable to write an out-of-range value.
        sa.CheckConstraint(
            "view_mode IN ('list', 'tiles')", name="ck_user_preferences_view_mode"
        ),
        schema="doc_library",
    )


def downgrade() -> None:
    op.drop_table("user_preferences", schema="doc_library")
