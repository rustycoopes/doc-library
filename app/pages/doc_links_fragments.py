"""HTML fragment routes backing the `/doc-library` page's inline add/edit/delete controls
(HTMX-driven, per the TDD's rendering-approach decision). Each mutation re-renders the whole
grouped-list partial (app/templates/partials/doc_links_list.html) - same underlying query/CRUD
functions as the JSON API (app/api/v1/doc_links.py), thin route-handler duplication only.

Unlike event-creator's Settings-shell fragments (app/pages/settings_fragments.py), which return a
200 reauth prompt for an unauthenticated request because they're eagerly loaded on page load,
these fragments are only ever reached via a user-initiated action (submit/delete) on an already-
authenticated page - a straightforward 401 (via `current_user_id`) is correct here, and is what
the WBS acceptance criteria require ("Unauthenticated requests to any ... fragment route return
401").
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.core.templating import templates
from app.db.session import get_db
from app.models.doc_link import DocLink, get_owned_doc_link, list_grouped_by_category
from app.schemas.doc_link import DocLinkCreate, DocLinkUpdate

router = APIRouter(prefix="/doc-library/fragments", tags=["fragments"])


async def _render_list(request: Request, db: AsyncSession, user_id: uuid.UUID) -> HTMLResponse:
    grouped_links = await list_grouped_by_category(db, user_id)
    return templates.TemplateResponse(
        request, "partials/doc_links_list.html", {"grouped_links": grouped_links}
    )


@router.post("/links", response_model=None)
async def create_link_fragment(
    request: Request,
    title: Annotated[str, Form()],
    url: Annotated[str, Form()],
    category: Annotated[str, Form()],
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    try:
        payload = DocLinkCreate(title=title, url=url, category=category)
    except ValidationError as exc:
        # include_context=False: pydantic's raw .errors() embeds the original exception object
        # (e.g. the ValueError our own field_validator raised) under "ctx" - not JSON-serializable
        # by FastAPI's default encoder, unlike RequestValidationError's own handling of this.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(include_context=False),
        ) from exc
    db.add(DocLink(user_id=user_id, title=payload.title, url=payload.url, category=payload.category))
    await db.commit()
    return await _render_list(request, db, user_id)


@router.patch("/links/{doc_link_id}", response_model=None)
async def update_link_fragment(
    request: Request,
    doc_link_id: uuid.UUID,
    title: Annotated[str, Form()],
    url: Annotated[str, Form()],
    category: Annotated[str, Form()],
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    doc_link = await get_owned_doc_link(db, doc_link_id, user_id)
    if doc_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        payload = DocLinkUpdate(title=title, url=url, category=category)
    except ValidationError as exc:
        # include_context=False: pydantic's raw .errors() embeds the original exception object
        # (e.g. the ValueError our own field_validator raised) under "ctx" - not JSON-serializable
        # by FastAPI's default encoder, unlike RequestValidationError's own handling of this.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(include_context=False),
        ) from exc
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(doc_link, field, value)
    await db.commit()
    return await _render_list(request, db, user_id)


@router.delete("/links/{doc_link_id}", response_model=None)
async def delete_link_fragment(
    request: Request,
    doc_link_id: uuid.UUID,
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    doc_link = await get_owned_doc_link(db, doc_link_id, user_id)
    if doc_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await db.delete(doc_link)
    await db.commit()
    return await _render_list(request, db, user_id)
