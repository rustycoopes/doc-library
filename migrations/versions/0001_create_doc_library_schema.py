"""Create the doc_library schema, migration role, and REFERENCES grant on host.users

Revision ID: 0001_create_doc_library_schema
Revises:
Create Date: 2026-07-17

Unlike event-creator's baseline (which adopted tables already moved by organize-me's R1
migration), doc_library never existed in the monolith — this is the first real DDL for this
app. Creates the schema and its own `doc_library_app` role (unused by the running app today,
same deferred-hardening gap noted in docs/secrets-and-accounts.md for host_app/event_creator_app),
plus the narrow REFERENCES-only grant on host.users the R1 pattern uses for cross-schema FKs
(see organize-me's d4e5f6a7b8c9_schema_separation_host_event_creator.py) — `doc_library_app`
must never be able to SELECT host.users, only reference it from a FK. No tables yet; those land
in a later slice once app/models/ has something to create.
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_create_doc_library_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS doc_library")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'doc_library_app') THEN
                CREATE ROLE doc_library_app NOLOGIN;
            END IF;
        END
        $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA doc_library TO doc_library_app")
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA doc_library TO doc_library_app")
    op.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA doc_library TO doc_library_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA doc_library GRANT ALL ON TABLES TO doc_library_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA doc_library GRANT ALL ON SEQUENCES TO doc_library_app"
    )

    # Narrow cross-schema grant: doc_library_app can reference host.users for its future FK
    # columns (doc_links.user_id, user_preferences.user_id), without being able to read it.
    op.execute("GRANT USAGE ON SCHEMA host TO doc_library_app")
    op.execute("GRANT REFERENCES ON host.users TO doc_library_app")


def downgrade() -> None:
    op.execute("REVOKE REFERENCES ON host.users FROM doc_library_app")
    op.execute("REVOKE USAGE ON SCHEMA host FROM doc_library_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA doc_library REVOKE ALL ON SEQUENCES FROM doc_library_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA doc_library REVOKE ALL ON TABLES FROM doc_library_app"
    )
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA doc_library FROM doc_library_app")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA doc_library FROM doc_library_app")
    op.execute("REVOKE USAGE ON SCHEMA doc_library FROM doc_library_app")
    op.execute("DROP ROLE IF EXISTS doc_library_app")
    op.execute("DROP SCHEMA IF EXISTS doc_library")
