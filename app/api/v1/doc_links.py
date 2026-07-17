"""Pure JSON CRUD for the current user's document links (Slice 3).

Every operation scopes to ``Depends(current_user_id)`` (raises 401 if unauthenticated - never a
redirect, this is an API surface). An id that isn't the requester's own returns 404, never 403 -
a 403 would leak that the row exists but belongs to someone else.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_db
from app.models.doc_link import DocLink, get_owned_doc_link
from app.schemas.doc_link import DocLinkCreate, DocLinkResponse, DocLinkUpdate

router = APIRouter(prefix="/api/v1", tags=["doc-links"])


@router.get("/doc-links", response_model=list[DocLinkResponse])
async def list_doc_links(
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[DocLink]:
    result = await db.scalars(
        select(DocLink).where(DocLink.user_id == user_id).order_by(DocLink.category, DocLink.title)
    )
    return list(result.all())


@router.post("/doc-links", response_model=DocLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_doc_link(
    payload: DocLinkCreate,
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DocLink:
    doc_link = DocLink(user_id=user_id, title=payload.title, url=payload.url, category=payload.category)
    db.add(doc_link)
    await db.commit()
    # created_at is a server_default (populated by Postgres on INSERT) - the session is
    # expire_on_commit=False, so without this refresh the Python attribute would still read None.
    await db.refresh(doc_link)
    return doc_link


@router.patch("/doc-links/{doc_link_id}", response_model=DocLinkResponse)
async def update_doc_link(
    doc_link_id: uuid.UUID,
    payload: DocLinkUpdate,
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DocLink:
    doc_link = await get_owned_doc_link(db, doc_link_id, user_id)
    if doc_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(doc_link, field, value)
    await db.commit()
    return doc_link


@router.delete("/doc-links/{doc_link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doc_link(
    doc_link_id: uuid.UUID,
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    doc_link = await get_owned_doc_link(db, doc_link_id, user_id)
    if doc_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await db.delete(doc_link)
    await db.commit()
