"""Dual static mount, old+new path (Slice 4 acceptance criteria) — see
docs/adr/static-asset-routing-mount-transition.md."""

from httpx import AsyncClient

from app.main import app


def test_new_prefixed_static_mount_resolves_to_doc_library_prefix() -> None:
    assert app.url_path_for("static", path="css/app.css") == "/doc-library/static/css/app.css"


def test_old_bare_static_mount_still_resolves() -> None:
    path = app.url_path_for("static_legacy_bare_path", path="css/app.css")
    assert path == "/static/css/app.css"


async def test_new_prefixed_static_mount_serves_real_content(client: AsyncClient) -> None:
    response = await client.get("/doc-library/static/css/app.css")

    assert response.status_code == 200
    assert len(response.content) > 0


async def test_old_bare_static_mount_still_serves_real_content(client: AsyncClient) -> None:
    response = await client.get("/static/css/app.css")

    assert response.status_code == 200
    assert len(response.content) > 0


async def test_old_and_new_static_mounts_serve_byte_identical_content(
    client: AsyncClient,
) -> None:
    new_response = await client.get("/doc-library/static/css/app.css")
    old_response = await client.get("/static/css/app.css")

    assert new_response.status_code == old_response.status_code == 200
    assert new_response.content == old_response.content
