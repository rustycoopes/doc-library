"""Fails loudly if the Tailwind build produced empty/near-empty output, or if the design tokens
didn't actually compile in - used by CI (ci.yml, deploy.yml) right after scripts/build_css.py so
a broken tokens.css import or a broken @source glob breaks the build instead of shipping an
unstyled app silently.
"""

import sys
from pathlib import Path

APP_CSS = Path(__file__).resolve().parent.parent / "app" / "static" / "css" / "app.css"
# A known-good build (doc-library#29, the TailAdmin tile redesign) is ~36.8KB. Set well below that
# so ordinary future growth doesn't false-positive, but comfortably above the ~29.6KB a real,
# silently-truncated build produced in the wild (Docker's build of this same script, run against
# the exact same commit ci.yml's "test" job had just built correctly, dropped ~20% of the output -
# see the Dockerfile's comment on this step). Bump this alongside deliberate, large template
# additions; don't lower it to make a truncated build pass.
MIN_BYTES = 30000

# Present only if the "Signal" @theme tokens were actually picked up - a dropped tokens.css import
# or a broken @source glob both fail this check.
CANARY_CLASS = ".bg-flame"

# Present only if doc_link_tile's flip-card markup (app/templates/partials/_doc_link_macros.html)
# was fully scanned - the specific class MIN_BYTES's regression floor exists to catch losing.
FLIP_CARD_CANARY = "backface-visibility:hidden"


def main() -> int:
    if not APP_CSS.is_file():
        print(f"::error::{APP_CSS} does not exist - did the Tailwind build step run?")
        return 1

    css = APP_CSS.read_text(encoding="utf-8")
    size = len(css.encode("utf-8"))
    print(f"Compiled app.css is {size} bytes")

    if size < MIN_BYTES:
        print(
            f"::error::app.css is suspiciously small ({size} bytes) - "
            "Tailwind build likely produced empty/near-empty output"
        )
        return 1

    if CANARY_CLASS not in css:
        print(
            f"::error::canary class {CANARY_CLASS} is missing from app.css - "
            "design tokens likely failed to compile in"
        )
        return 1

    if FLIP_CARD_CANARY not in css:
        print(
            f"::error::canary rule {FLIP_CARD_CANARY!r} is missing from app.css - "
            "the build likely produced incomplete output (see this script's comment)"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
