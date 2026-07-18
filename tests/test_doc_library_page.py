"""Slice 2 acceptance criteria: /doc-library trusts the Host JWT (signature + expiry only) with no
login/session logic of its own, renders the shared chrome (including dark-mode) for a logged-in
user, and redirects an unauthenticated visitor to the Host's login - proving the cross-repo trust
seam end to end before any real feature logic is built.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TokenFactory, create_doc_link, create_host_user, create_user_preference


async def test_valid_host_jwt_renders_the_empty_state_page(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))

    response = await client.get(
        "/doc-library", cookies={"organizeme_auth": token}, follow_redirects=False
    )

    assert response.status_code == 200
    assert "Doc Library" in response.text
    assert "No links saved yet" in response.text


async def test_no_cookie_redirects_to_host_login(client: AsyncClient) -> None:
    response = await client.get("/doc-library", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


async def test_expired_token_redirects_to_host_login(
    client: AsyncClient, make_token: type[TokenFactory]
) -> None:
    token = make_token.expired()

    response = await client.get(
        "/doc-library", cookies={"organizeme_auth": token}, follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


async def test_tampered_signature_redirects_to_host_login(
    client: AsyncClient, make_token: type[TokenFactory]
) -> None:
    token = make_token.tampered()

    response = await client.get(
        "/doc-library", cookies={"organizeme_auth": token}, follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


async def test_garbage_cookie_value_redirects_to_host_login(client: AsyncClient) -> None:
    response = await client.get(
        "/doc-library", cookies={"organizeme_auth": "not-a-jwt"}, follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


async def test_wrong_audience_redirects_to_host_login(
    client: AsyncClient, make_token: type[TokenFactory]
) -> None:
    token = make_token.wrong_audience()

    response = await client.get(
        "/doc-library", cookies={"organizeme_auth": token}, follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


async def test_missing_sub_claim_redirects_to_host_login(
    client: AsyncClient, make_token: type[TokenFactory]
) -> None:
    token = make_token.missing_sub()

    response = await client.get(
        "/doc-library", cookies={"organizeme_auth": token}, follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


async def test_non_uuid_sub_claim_redirects_to_host_login_instead_of_500(
    client: AsyncClient, make_token: type[TokenFactory]
) -> None:
    # Regression test for the fix in app/core/auth.py: a signature/expiry/audience-valid token
    # whose sub isn't a UUID string must redirect like any other untrusted token, not 500.
    token = make_token.non_uuid_sub()

    response = await client.get(
        "/doc-library", cookies={"organizeme_auth": token}, follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


async def test_alg_none_token_redirects_to_host_login(
    client: AsyncClient, make_token: type[TokenFactory]
) -> None:
    # Regression test locking in verify_token()'s explicit algorithms=["HS256"] pin against the
    # classic alg=none JWT bypass.
    token = make_token.alg_none()

    response = await client.get(
        "/doc-library", cookies={"organizeme_auth": token}, follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


async def test_doc_library_page_applies_the_hosts_dark_mode_preference(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session, dark_mode=True)
    token = make_token.valid(sub=str(user_id))

    response = await client.get("/doc-library", cookies={"organizeme_auth": token})

    assert response.status_code == 200
    assert 'data-theme="dark"' in response.text


async def test_doc_library_page_defaults_to_light_mode(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session, dark_mode=False)
    token = make_token.valid(sub=str(user_id))

    response = await client.get("/doc-library", cookies={"organizeme_auth": token})

    assert response.status_code == 200
    assert 'data-theme="corporate"' in response.text


async def test_doc_library_present_in_sidebar_nav(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))

    response = await client.get("/doc-library", cookies={"organizeme_auth": token})

    assert response.status_code == 200
    assert 'href="/doc-library"' in response.text


async def test_page_renders_links_grouped_by_category(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))
    await create_doc_link(db_session, user_id=user_id, title="Zebra Guide", category="Beta")
    await create_doc_link(db_session, user_id=user_id, title="Apple Guide", category="Alpha")

    response = await client.get("/doc-library", cookies={"organizeme_auth": token})

    assert response.status_code == 200
    assert "No links saved yet" not in response.text
    assert "Alpha" in response.text
    assert "Beta" in response.text
    # Alpha's category heading appears before Beta's - alphabetical category ordering.
    assert response.text.index("Alpha") < response.text.index("Beta")


async def test_page_still_shows_empty_state_with_zero_links(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))

    response = await client.get("/doc-library", cookies={"organizeme_auth": token})

    assert response.status_code == 200
    assert "No links saved yet" in response.text


async def test_page_defaults_to_list_view_when_no_preference_row_exists(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    token = make_token.valid(sub=str(user_id))
    await create_doc_link(db_session, user_id=user_id, title="MDN", category="Reference")

    response = await client.get("/doc-library", cookies={"organizeme_auth": token})

    assert response.status_code == 200
    assert 'data-view-mode="list"' in response.text


async def test_page_renders_tiles_when_the_user_has_persisted_that_preference(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    user_id = await create_host_user(db_session)
    await create_user_preference(db_session, user_id=user_id, view_mode="tiles")
    token = make_token.valid(sub=str(user_id))
    await create_doc_link(db_session, user_id=user_id, title="MDN", category="Reference")

    response = await client.get("/doc-library", cookies={"organizeme_auth": token})

    assert response.status_code == 200
    assert 'data-view-mode="tiles"' in response.text


async def test_tile_view_groups_categories_and_titles_alphabetically(
    client: AsyncClient, db_session: AsyncSession, make_token: type[TokenFactory]
) -> None:
    # Mirrors test_page_renders_links_grouped_by_category's list-mode assertion - the WBS
    # requires tile view to use the same grouping/ordering rules as list view, not just the same
    # layout mechanism.
    user_id = await create_host_user(db_session)
    await create_user_preference(db_session, user_id=user_id, view_mode="tiles")
    token = make_token.valid(sub=str(user_id))
    await create_doc_link(db_session, user_id=user_id, title="Zebra Guide", category="Beta")
    await create_doc_link(db_session, user_id=user_id, title="Banana Guide", category="Alpha")
    await create_doc_link(db_session, user_id=user_id, title="Apple Guide", category="Alpha")

    response = await client.get("/doc-library", cookies={"organizeme_auth": token})

    assert response.status_code == 200
    assert 'data-view-mode="tiles"' in response.text
    # Category ordering: Alpha before Beta.
    assert response.text.index("Alpha") < response.text.index("Beta")
    # Title ordering within a category: Apple before Banana.
    assert response.text.index("Apple Guide") < response.text.index("Banana Guide")
