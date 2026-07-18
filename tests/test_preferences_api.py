"""JSON API for the current user's view-mode preference (Slice 4 acceptance criteria)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TokenFactory, create_host_user, create_user_preference


async def test_update_preference_requires_authentication(client: AsyncClient) -> None:
    response = await client.put("/api/v1/doc-links/preferences", json={"view_mode": "tiles"})

    assert response.status_code == 401


async def test_update_preference_creates_row_on_first_write_and_returns_it(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))

    response = await client.put(
        "/api/v1/doc-links/preferences",
        json={"view_mode": "tiles"},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 200
    assert response.json() == {"view_mode": "tiles"}


async def test_update_preference_persists_and_a_second_write_reads_back_the_new_value(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))
    cookies = {"organizeme_auth": token}

    first = await client.put(
        "/api/v1/doc-links/preferences", json={"view_mode": "tiles"}, cookies=cookies
    )
    assert first.status_code == 200
    assert first.json()["view_mode"] == "tiles"

    second = await client.put(
        "/api/v1/doc-links/preferences", json={"view_mode": "list"}, cookies=cookies
    )
    assert second.status_code == 200
    assert second.json()["view_mode"] == "list"


async def test_update_preference_rejects_invalid_view_mode(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))

    response = await client.put(
        "/api/v1/doc-links/preferences",
        json={"view_mode": "grid"},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 422


async def test_update_preference_overwrites_an_existing_row(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    await create_user_preference(db_session, user_id=user_id, view_mode="tiles")
    token = make_token.valid(sub=str(user_id))

    response = await client.put(
        "/api/v1/doc-links/preferences",
        json={"view_mode": "list"},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 200
    assert response.json() == {"view_mode": "list"}


async def test_update_preference_does_not_affect_another_users_preference(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    from app.models.user_preference import get_view_mode

    owner_id = await create_host_user(db_session)
    other_id = await create_host_user(db_session)
    other_token = make_token.valid(sub=str(other_id))

    response = await client.put(
        "/api/v1/doc-links/preferences",
        json={"view_mode": "tiles"},
        cookies={"organizeme_auth": other_token},
    )

    assert response.status_code == 200
    assert await get_view_mode(db_session, owner_id) == "list"
