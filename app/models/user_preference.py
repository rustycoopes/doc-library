"""A user's persisted view-mode preference for `/doc-library` (Slice 4).

No row exists until a user's first write - ``get_view_mode`` defaults to ``DEFAULT_VIEW_MODE``
when the row is absent rather than creating one, and ``set_view_mode`` is the only path that ever
writes a row, per the TDD's lazy-creation decision (mirrors event_creator.user_settings).
"""

import uuid
from typing import Literal

from sqlalchemy import ForeignKey, Text, Uuid, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ViewMode = Literal["list", "tiles"]
DEFAULT_VIEW_MODE: ViewMode = "list"


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = {"schema": "doc_library"}

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("host.users.id", ondelete="cascade"), primary_key=True
    )
    view_mode: Mapped[str] = mapped_column(Text, nullable=False)


async def get_view_mode(db: AsyncSession, user_id: uuid.UUID) -> str:
    """The user's persisted ``view_mode``, or ``DEFAULT_VIEW_MODE`` if no row exists yet.

    Read-only - never creates a row, so a page load alone doesn't cause a write.
    """
    preference = await db.scalar(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    return preference.view_mode if preference is not None else DEFAULT_VIEW_MODE


async def set_view_mode(db: AsyncSession, user_id: uuid.UUID, view_mode: ViewMode) -> ViewMode:
    """Persists ``view_mode``, creating the row on a user's first write.

    An atomic ``INSERT ... ON CONFLICT DO UPDATE`` rather than select-then-insert/update, so two
    concurrent first-writes for the same user can't race each other into a duplicate-PK error.

    Does not commit - matches ``app/models/doc_link.py``'s convention of leaving the transaction
    boundary to the calling route handler.
    """
    stmt = pg_insert(UserPreference).values(user_id=user_id, view_mode=view_mode)
    stmt = stmt.on_conflict_do_update(
        index_elements=[UserPreference.user_id], set_={"view_mode": view_mode}
    )
    await db.execute(stmt)
    return view_mode
