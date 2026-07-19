import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# doc-library#22: nothing in this app ever configured the root logger, so every logger.info()/
# .debug() call anywhere in app/ (including the registry refresh loop's own instrumentation) was
# silently dropped by Python's default root level (WARNING) - only .warning()+ calls ever reached
# Cloud Run's logs (via logging.lastResort's stderr handler). Confirmed live: "registry refresh:
# freshly-refreshed" never once appeared in QA logs despite the registry having demonstrably
# refreshed successfully. This makes INFO+ visible app-wide, matching uvicorn's own already-visible
# INFO access logs, called before any other import has a chance to emit anything.
logging.basicConfig(level=logging.INFO)

# Imported first, deliberately - configures organizeme_chrome's registry source (see
# app/core/registry.py's module docstring) before any router module below can call
# organizeme_chrome.get_app()/list_apps() at its own module-import time (app/core/templating.py
# does exactly this, transitively, via every app/pages/* router imported below).
from app.core import registry as _registry  # noqa: F401
from app.api.v1.doc_links import router as doc_links_api_router
from app.api.v1.preferences import router as preferences_api_router
from app.core.config import get_settings
from app.core.registry import (
    configure_client_registry_source,
    start_registry_refresh_task,
    stop_registry_refresh_task,
)
from app.pages.doc_library import router as doc_library_router
from app.pages.doc_links_fragments import router as doc_links_fragments_router

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Registry-decoupling (organize-me#219): serve this service's own nav/Settings/API surface
    # (SELF_APP_ENTRY) until the first successful background fetch from the Host replaces it -
    # see app/core/registry.py and docs/features/registry-decoupling/TDD.md in organize-me.
    settings = get_settings()
    registry_source = configure_client_registry_source()
    refresh_task, refresh_client = start_registry_refresh_task(registry_source, settings)

    yield

    await stop_registry_refresh_task(refresh_task, refresh_client)
    # Imported here, not at module level, so importing app.main (e.g. for /health tests that
    # never touch the DB) doesn't force DATABASE_URL/Settings to be resolved at import time.
    from app.db.session import get_engine

    await get_engine().dispose()


app = FastAPI(title="Doc Library", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(doc_library_router)
app.include_router(doc_links_api_router)
app.include_router(preferences_api_router)
app.include_router(doc_links_fragments_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
