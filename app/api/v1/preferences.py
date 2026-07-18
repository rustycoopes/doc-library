"""Pure JSON endpoint for the current user's view-mode preference (Slice 4).

Scoped to ``Depends(current_user_id)`` (401 if unauthenticated) exactly like
``app/api/v1/doc_links.py`` - a user's preference row is never readable or writable via anyone
else's id.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_db
from app.models.user_preference import set_view_mode
from app.schemas.user_preference import ViewModePreference

router = APIRouter(prefix="/api/v1", tags=["preferences"])


@router.put("/doc-links/preferences", response_model=ViewModePreference)
async def update_view_mode_preference(
    payload: ViewModePreference,
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ViewModePreference:
    view_mode = await set_view_mode(db, user_id, payload.view_mode)
    await db.commit()
    return ViewModePreference(view_mode=view_mode)
