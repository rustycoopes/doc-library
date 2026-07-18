from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.doc_links import router as doc_links_api_router
from app.api.v1.preferences import router as preferences_api_router
from app.pages.doc_library import router as doc_library_router
from app.pages.doc_links_fragments import router as doc_links_fragments_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    # Imported here, not at module level, so importing app.main (e.g. for /health tests that
    # never touch the DB) doesn't force DATABASE_URL/Settings to be resolved at import time.
    from app.db.session import get_engine

    await get_engine().dispose()


app = FastAPI(title="Doc Library", lifespan=lifespan)
app.include_router(doc_library_router)
app.include_router(doc_links_api_router)
app.include_router(preferences_api_router)
app.include_router(doc_links_fragments_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
