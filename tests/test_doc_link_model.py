"""DB-level behavior of doc_library.doc_links that isn't reachable through the HTTP API,
matching the R10 pattern (event-creator's test_event_model.py)."""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.doc_link import DocLink, list_grouped_by_category
from tests.conftest import create_doc_link, create_host_user


async def test_deleting_host_user_cascades_to_doc_links(db_session: AsyncSession) -> None:
    user_id = await create_host_user(db_session)
    doc_link_id = await create_doc_link(db_session, user_id=user_id)

    await db_session.execute(text("DELETE FROM host.users WHERE id = :id"), {"id": user_id})
    await db_session.flush()

    remaining = await db_session.scalar(select(DocLink).where(DocLink.id == doc_link_id))
    assert remaining is None


async def test_list_grouped_by_category_orders_categories_and_titles_alphabetically(
    db_session: AsyncSession,
) -> None:
    user_id = await create_host_user(db_session)
    await create_doc_link(db_session, user_id=user_id, title="Zebra", category="Beta")
    await create_doc_link(db_session, user_id=user_id, title="Banana", category="Alpha")
    await create_doc_link(db_session, user_id=user_id, title="Apple", category="Alpha")

    grouped = await list_grouped_by_category(db_session, user_id)

    categories = [category for category, _ in grouped]
    assert categories == sorted(categories)
    alpha_titles = [link.title for category, links in grouped if category == "Alpha" for link in links]
    assert alpha_titles == ["Apple", "Banana"]


async def test_list_grouped_by_category_returns_empty_list_for_no_links(
    db_session: AsyncSession,
) -> None:
    user_id = await create_host_user(db_session)

    grouped = await list_grouped_by_category(db_session, user_id)

    assert grouped == []
