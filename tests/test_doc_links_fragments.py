"""HTMX fragment routes backing the /doc-library page's inline add/edit/delete controls."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TokenFactory, create_doc_link, create_host_user


async def test_create_fragment_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/doc-library/fragments/links",
        data={"title": "T", "url": "https://example.com", "category": "C"},
    )

    assert response.status_code == 401


async def test_edit_fragment_requires_authentication(client: AsyncClient) -> None:
    response = await client.patch(
        f"/doc-library/fragments/links/{uuid.uuid4()}",
        data={"title": "T", "url": "https://example.com", "category": "C"},
    )

    assert response.status_code == 401


async def test_delete_fragment_requires_authentication(client: AsyncClient) -> None:
    response = await client.delete(f"/doc-library/fragments/links/{uuid.uuid4()}")

    assert response.status_code == 401


async def test_create_fragment_returns_rerendered_list_with_new_link(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))

    response = await client.post(
        "/doc-library/fragments/links",
        data={"title": "MDN", "url": "https://developer.mozilla.org", "category": "Reference"},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 200
    assert "MDN" in response.text
    assert "Reference" in response.text
    assert 'id="doc-links-list"' in response.text


async def test_create_fragment_rejects_invalid_url(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))

    response = await client.post(
        "/doc-library/fragments/links",
        data={"title": "T", "url": "not-a-url", "category": "C"},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 422


async def test_edit_fragment_returns_rerendered_list_with_updated_link(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))
    doc_link_id = await create_doc_link(db_session, user_id=user_id, title="Old Name")

    response = await client.patch(
        f"/doc-library/fragments/links/{doc_link_id}",
        data={"title": "New Name", "url": "https://example.com", "category": "General"},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 200
    assert "New Name" in response.text
    assert "Old Name" not in response.text


async def test_edit_fragment_another_users_link_returns_404(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    owner_id = await create_host_user(db_session)
    other_id = await create_host_user(db_session)
    other_token = make_token.valid(sub=str(other_id))
    doc_link_id = await create_doc_link(db_session, user_id=owner_id)

    response = await client.patch(
        f"/doc-library/fragments/links/{doc_link_id}",
        data={"title": "Hijacked", "url": "https://example.com", "category": "General"},
        cookies={"organizeme_auth": other_token},
    )

    assert response.status_code == 404


async def test_delete_fragment_returns_rerendered_list_without_link(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))
    doc_link_id = await create_doc_link(db_session, user_id=user_id, title="To Delete")

    response = await client.delete(
        f"/doc-library/fragments/links/{doc_link_id}", cookies={"organizeme_auth": token}
    )

    assert response.status_code == 200
    assert "To Delete" not in response.text
    assert 'id="doc-links-list"' in response.text


async def test_delete_fragment_another_users_link_returns_404(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    owner_id = await create_host_user(db_session)
    other_id = await create_host_user(db_session)
    other_token = make_token.valid(sub=str(other_id))
    doc_link_id = await create_doc_link(db_session, user_id=owner_id)

    response = await client.delete(
        f"/doc-library/fragments/links/{doc_link_id}", cookies={"organizeme_auth": other_token}
    )

    assert response.status_code == 404


async def test_delete_fragment_shows_empty_state_when_last_link_removed(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))
    doc_link_id = await create_doc_link(db_session, user_id=user_id)

    response = await client.delete(
        f"/doc-library/fragments/links/{doc_link_id}", cookies={"organizeme_auth": token}
    )

    assert response.status_code == 200
    assert "No links saved yet" in response.text
