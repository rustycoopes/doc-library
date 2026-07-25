# ---- Build stage: compiles the Tailwind CSS build. The ~35-40MB Tailwind CLI binary and the
# build-only Python packages that fetch it never reach the runtime image below - see
# docs/adr/design-refresh-per-service-tailwind-build.md (organize-me). The compile step (below) is
# a separate RUN layer from `COPY app`, but Docker's cache invalidation still cascades correctly:
# any change under app/ invalidates `COPY app` and therefore forces the compile layer to rerun too,
# so cached CSS can never silently drift out of sync with the templates it was built from.
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --group build --no-install-project

COPY app ./app
COPY scripts ./scripts
RUN uv run python scripts/build_css.py
# TEMP DEBUG - remove before merge
RUN cat app/static/css/.generated-entry.css \
    && CHROME_DIR=$(uv run python -c "from organizeme_chrome.paths import chrome_templates_dir; print(chrome_templates_dir())") \
    && echo "chrome templates dir: $CHROME_DIR" \
    && find "$CHROME_DIR" -name "*.html" | sort \
    && echo "app templates:" \
    && find app/templates -name "*.html" | sort \
    && echo "tailwindcss binary:" \
    && find / -iname "tailwindcss-linux-x64*" -type f 2>/dev/null -exec ls -la {} \; \
    && which tailwindcss 2>&1 || true \
    && wc -c app/static/css/app.css
# Docker's own build (unlike ci.yml's separate "test" job) had no check on the compiled CSS at
# all - a doc-library#29 deploy shipped a silently-truncated app.css (missing everything from the
# tile redesign: the 3D-flip transforms, several accent-tint classes) because nothing here caught
# it; ci.yml's test job ran the same script against the same commit moments earlier and got the
# full file, so this was a build-time flake (most likely the tailwindcss-linux-x64 binary download
# from GitHub Releases racing/timing out under Docker's network path), not a code bug. This step
# makes that class of failure fail the build instead of shipping.
RUN uv run python scripts/verify_css_build.py

# ---- Runtime stage: no Tailwind CLI, no build-only Python packages - only the compiled
# stylesheet and fonts are copied in from the builder stage.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# git is required at build time because organizeme-chrome is a git dependency - uv sync needs
# git on PATH to resolve/clone it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY --from=builder /app/app/static/css/app.css ./app/static/css/app.css
COPY --from=builder /app/app/static/fonts ./app/static/fonts

RUN uv sync --frozen --no-dev

EXPOSE 8080

# Listens on Cloud Run's injected $PORT (defaults to 8080 for a fresh service). Wrapped in
# /bin/sh -c because CMD's exec form does not perform shell/env-var expansion on its own.
#
# --forwarded-allow-ips='*' trusts the X-Forwarded-Proto header from whatever peer connects to
# the container. Cloud Run terminates TLS at its own front end and always proxies to the
# container over a private, single-hop connection - the container is never reachable except
# through that proxy - so this is safe here.
CMD ["/bin/sh", "-c", "/app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'"]
