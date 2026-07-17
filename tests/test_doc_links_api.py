"""JSON CRUD API for the current user's doc links (Slice 3 acceptance criteria)."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TokenFactory, create_doc_link, create_host_user


async def test_list_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/doc-links")

    assert response.status_code == 401


async def test_create_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/doc-links", json={"title": "T", "url": "https://example.com", "category": "C"}
    )

    assert response.status_code == 401


async def test_patch_requires_authentication(client: AsyncClient) -> None:
    response = await client.patch(f"/api/v1/doc-links/{uuid.uuid4()}", json={"title": "T"})

    assert response.status_code == 401


async def test_delete_requires_authentication(client: AsyncClient) -> None:
    response = await client.delete(f"/api/v1/doc-links/{uuid.uuid4()}")

    assert response.status_code == 401


async def test_create_then_list_returns_the_new_link(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))
    cookies = {"organizeme_auth": token}

    create_response = await client.post(
        "/api/v1/doc-links",
        json={"title": "FastAPI Docs", "url": "https://fastapi.tiangolo.com", "category": "Backend"},
        cookies=cookies,
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["title"] == "FastAPI Docs"
    assert body["category"] == "Backend"
    assert "id" in body
    assert "created_at" in body

    list_response = await client.get("/api/v1/doc-links", cookies=cookies)
    assert list_response.status_code == 200
    titles = [link["title"] for link in list_response.json()]
    assert "FastAPI Docs" in titles


async def test_create_rejects_empty_title(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))

    response = await client.post(
        "/api/v1/doc-links",
        json={"title": "   ", "url": "https://example.com", "category": "C"},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 422


async def test_create_rejects_empty_category(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))

    response = await client.post(
        "/api/v1/doc-links",
        json={"title": "T", "url": "https://example.com", "category": "  "},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 422


async def test_create_rejects_non_http_url(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))

    response = await client.post(
        "/api/v1/doc-links",
        json={"title": "T", "url": "ftp://example.com/file", "category": "C"},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 422


async def test_create_rejects_url_with_no_host(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))

    response = await client.post(
        "/api/v1/doc-links",
        json={"title": "T", "url": "https://", "category": "C"},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 422


async def test_patch_updates_fields_and_returns_200(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))
    doc_link_id = await create_doc_link(db_session, user_id=user_id, title="Old Title")

    response = await client.patch(
        f"/api/v1/doc-links/{doc_link_id}",
        json={"title": "New Title"},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


async def test_patch_rejects_explicit_null_title_with_422_not_500(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    # Regression test: DocLinkUpdate's fields are `str | None` so a field can be *omitted*
    # ("not supplied"), but an explicit JSON null must still be rejected, not silently applied -
    # title/category/url are all NOT NULL columns, so letting null through used to 500 on commit.
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))
    doc_link_id = await create_doc_link(db_session, user_id=user_id)

    response = await client.patch(
        f"/api/v1/doc-links/{doc_link_id}",
        json={"title": None},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 422


async def test_create_rejects_javascript_scheme_url(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))

    response = await client.post(
        "/api/v1/doc-links",
        json={"title": "T", "url": "javascript:alert(1)", "category": "C"},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 422


async def test_patch_rejects_empty_title(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))
    doc_link_id = await create_doc_link(db_session, user_id=user_id)

    response = await client.patch(
        f"/api/v1/doc-links/{doc_link_id}",
        json={"title": "   "},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 422


async def test_patch_rejects_empty_category(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))
    doc_link_id = await create_doc_link(db_session, user_id=user_id)

    response = await client.patch(
        f"/api/v1/doc-links/{doc_link_id}",
        json={"category": "   "},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 422


async def test_patch_rejects_non_http_url(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))
    doc_link_id = await create_doc_link(db_session, user_id=user_id)

    response = await client.patch(
        f"/api/v1/doc-links/{doc_link_id}",
        json={"url": "ftp://example.com/file"},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 422


async def test_patch_nonexistent_id_returns_404(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))

    response = await client.patch(
        f"/api/v1/doc-links/{uuid.uuid4()}",
        json={"title": "New Title"},
        cookies={"organizeme_auth": token},
    )

    assert response.status_code == 404


async def test_patch_another_users_link_returns_404_not_403(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    owner_id = await create_host_user(db_session)
    other_id = await create_host_user(db_session)
    other_token = make_token.valid(sub=str(other_id))
    doc_link_id = await create_doc_link(db_session, user_id=owner_id)

    response = await client.patch(
        f"/api/v1/doc-links/{doc_link_id}",
        json={"title": "Hijacked"},
        cookies={"organizeme_auth": other_token},
    )

    assert response.status_code == 404


async def test_delete_removes_the_row(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))
    doc_link_id = await create_doc_link(db_session, user_id=user_id)

    delete_response = await client.delete(
        f"/api/v1/doc-links/{doc_link_id}", cookies={"organizeme_auth": token}
    )
    assert delete_response.status_code == 204

    list_response = await client.get("/api/v1/doc-links", cookies={"organizeme_auth": token})
    assert all(link["id"] != str(doc_link_id) for link in list_response.json())


async def test_delete_another_users_link_returns_404(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    owner_id = await create_host_user(db_session)
    other_id = await create_host_user(db_session)
    other_token = make_token.valid(sub=str(other_id))
    doc_link_id = await create_doc_link(db_session, user_id=owner_id)

    response = await client.delete(
        f"/api/v1/doc-links/{doc_link_id}", cookies={"organizeme_auth": other_token}
    )

    assert response.status_code == 404


async def test_delete_nonexistent_id_returns_404(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))

    response = await client.delete(
        f"/api/v1/doc-links/{uuid.uuid4()}", cookies={"organizeme_auth": token}
    )

    assert response.status_code == 404


async def test_list_has_no_pagination_cap(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))
    for i in range(60):
        await create_doc_link(db_session, user_id=user_id, title=f"Link {i}", category="Bulk")

    response = await client.get("/api/v1/doc-links", cookies={"organizeme_auth": token})

    assert response.status_code == 200
    assert len(response.json()) >= 60
