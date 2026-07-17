"""The `/doc-library` page (Slice 2 SSO-trust tracer bullet; Slice 3 adds real content).

Trusts the Host-issued JWT (signature + expiry only) with no login/session logic of its own - see
app.core.auth. A relative redirect to /login is correct (not an absolute Host URL): both services
sit behind the same shared Load Balancer origin, and /login is a Host-owned path in the URL map,
so the browser's next request for it is routed back to the Host automatically.
"""

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id_optional
from app.core.nav import sidebar_nav_context
from app.core.templating import templates
from app.db.session import get_db
from app.models.doc_link import list_grouped_by_category
from app.services.host_user import get_host_user

router = APIRouter(tags=["pages"])


@router.get("/doc-library", response_model=None)
async def doc_library_page(
    request: Request,
    user_id: uuid.UUID | None = Depends(current_user_id_optional),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Redirects to the Host's `/login` when unauthenticated; otherwise renders the user's links
    grouped by category (or the empty state, if they have none) with the shared chrome, reading
    `dark_mode` from the Host's own stored preference.
    """
    if user_id is None:
        return RedirectResponse("/login", status_code=302)

    # host_user is None only in the defensive case get_host_user() already handles (a JWT for a
    # Host user id that no longer resolves to a row) - falls back to light mode, same as a user
    # who has never set the preference.
    host_user = await get_host_user(db, user_id)
    grouped_links = await list_grouped_by_category(db, user_id)
    context = {
        "dark_mode": host_user.dark_mode if host_user is not None else False,
        "grouped_links": grouped_links,
        **sidebar_nav_context(host_user, request),
    }
    return templates.TemplateResponse(request, "pages/doc_library.html", context)
