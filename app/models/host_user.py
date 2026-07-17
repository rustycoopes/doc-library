"""Read-only mapping onto the Host's `host.users` table (Slice 2, R7 gotcha pattern).

Doc Library owns no `User`/fastapi-users model of its own (see app.core.auth's docstring) - the
Host-issued JWT tells us *which* user id is making a request, nothing more. The empty-state page
needs the Host's `dark_mode` preference so the shared chrome renders in the user's actual theme
instead of defaulting to light.

`HostUser` is mapped onto `host.users` - the same Postgres database, a cross-schema query, no
network call - but is **select-only by convention and by construction**:

- It's mapped on the same `app.db.base.Base` as every other model here, NOT a separate metadata -
  a string-based `ForeignKey("host.users.id")` (doc_links.user_id, user_preferences.user_id, added
  in a later slice) only resolves against a table registered in the *same* `MetaData`. Safety from
  Alembic autogenerate ever managing this table instead comes from `migrations/env.py`'s
  `include_object` filter, which excludes the `host` schema outright.
- Only the columns this service actually reads are declared (`id`, `dark_mode`,
  `nav_collapsed_groups`) - deliberately omitting `email`, `hashed_password`, `is_active`, etc.,
  which live on the Host's real `User` model and are none of Doc Library's concern.
- Nothing in this codebase ever `db.add()`s, updates, or deletes a `HostUser` - callers must only
  ever `select()` it. There is no ORM-level mechanism preventing a write, so this is enforced by
  code review / convention, same as event-creator's identical pattern.
"""

import uuid

from sqlalchemy import JSON, Boolean, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HostUser(Base):
    """SELECT-ONLY. Never insert/update/delete through this class - see module docstring."""

    __tablename__ = "users"
    __table_args__ = {"schema": "host"}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    dark_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    nav_collapsed_groups: Mapped[dict[str, bool]] = mapped_column(JSON, default=dict)
