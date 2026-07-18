"""DB-level behavior of doc_library.user_preferences that isn't reachable through the HTTP API,
matching the R10 pattern (event-creator's test_event_model.py / this repo's
test_doc_link_model.py)."""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preference import UserPreference, get_view_mode, set_view_mode
from tests.conftest import create_host_user, create_user_preference


async def test_get_view_mode_defaults_to_list_with_no_row(db_session: AsyncSession) -> None:
    user_id = await create_host_user(db_session)

    assert await get_view_mode(db_session, user_id) == "list"


async def test_get_view_mode_does_not_create_a_row(db_session: AsyncSession) -> None:
    user_id = await create_host_user(db_session)

    await get_view_mode(db_session, user_id)

    row = await db_session.scalar(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    assert row is None


async def test_set_view_mode_creates_a_row_on_first_write(db_session: AsyncSession) -> None:
    user_id = await create_host_user(db_session)

    result = await set_view_mode(db_session, user_id, "tiles")

    assert result == "tiles"
    assert await get_view_mode(db_session, user_id) == "tiles"


async def test_set_view_mode_updates_an_existing_row(db_session: AsyncSession) -> None:
    user_id = await create_host_user(db_session)
    await create_user_preference(db_session, user_id=user_id, view_mode="tiles")

    result = await set_view_mode(db_session, user_id, "list")

    assert result == "list"
    assert await get_view_mode(db_session, user_id) == "list"


async def test_deleting_host_user_cascades_to_user_preferences(db_session: AsyncSession) -> None:
    user_id = await create_host_user(db_session)
    await create_user_preference(db_session, user_id=user_id)

    await db_session.execute(text("DELETE FROM host.users WHERE id = :id"), {"id": user_id})
    await db_session.flush()

    remaining = await db_session.scalar(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    assert remaining is None
