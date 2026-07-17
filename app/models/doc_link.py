"""A single user-saved documentation link (Slice 3 - the feature's core entity).

No ordering column: ``list_grouped_by_category`` computes ``ORDER BY category, title`` at query
time and groups in Python, per the TDD's layering decision (no dedicated service layer -
see docs/features/doc-library/TDD.md's Layering section).
"""

import itertools
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, Uuid, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocLink(Base):
    __tablename__ = "doc_links"
    __table_args__ = {"schema": "doc_library"}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("host.users.id", ondelete="cascade"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


async def list_grouped_by_category(
    db: AsyncSession, user_id: uuid.UUID
) -> list[tuple[str, list["DocLink"]]]:
    """The user's links ordered ``category, title`` and grouped by category in Python.

    ``itertools.groupby`` only groups *consecutive* runs, so this relies on the query's own
    ``ORDER BY category`` to make each category's rows contiguous - it does not re-sort.
    """
    result = await db.scalars(
        select(DocLink)
        .where(DocLink.user_id == user_id)
        .order_by(DocLink.category, DocLink.title)
    )
    links = list(result.all())
    return [(category, list(group)) for category, group in itertools.groupby(links, key=lambda link: link.category)]


async def get_owned_doc_link(
    db: AsyncSession, doc_link_id: uuid.UUID, user_id: uuid.UUID
) -> DocLink | None:
    """The link if it exists and belongs to ``user_id``, else ``None`` - shared by ``PATCH`` and
    ``DELETE`` so both give the same 404 whether the id doesn't exist at all or belongs to
    another user, never confirming another user's link exists."""
    doc_link: DocLink | None = await db.scalar(
        select(DocLink).where(DocLink.id == doc_link_id, DocLink.user_id == user_id)
    )
    return doc_link
