"""doc-library#16: regression test for the registry-source import-ordering invariant that
Registry-decoupling Slice 3 (organize-me#220) broke and PR #15 fixed - `app/core/registry.py`
must be imported (and self-configure a source) before any router that transitively calls
`organizeme_chrome.get_app()`/`list_apps()` at *its own* import time (`app/pages/doc_library.py`,
via `app/core/templating.py`). Before the fix, `app/main.py` only configured a source inside
`lifespan`, which runs after every module-level import completes - a fresh `uvicorn app.main:app`
process crashed at import time (confirmed live via a doc-library-qa Cloud Run deploy failure).

This can't be a plain in-process `import app.main` test like organize-me's own
`tests/test_registry_wiring.py`: `tests/conftest.py` already calls
`configure_client_registry_source()` at its own module-import time (its docstring explains why -
the `client` fixture's ASGITransport never runs `lifespan`), which runs before pytest collects any
test module in this directory. That forces a correct source into place regardless of whether
`app/main.py`'s *own* internal import order is actually correct, which would blind an in-process
version of this test to exactly the regression it exists to catch. Spawning a subprocess with a
fresh interpreter (no conftest involved) is what actually reproduces the real container-startup
path (`uvicorn app.main:app`) that broke in production.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_importing_app_main_resolves_the_registry_source_without_raising() -> None:
    probe = (
        "import app.main\n"
        "from app.core.registry import SELF_APP_ENTRY\n"
        "from organizeme_chrome.registry import list_apps\n"
        "assert list_apps() == [SELF_APP_ENTRY], list_apps()\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
