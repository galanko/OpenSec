# =============================================================================
# OpenSec — Multi-stage Docker build
# Stage 1: Build frontend (Node)
# Stage 2: Production runtime (Python + OpenCode Go binary)
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Frontend build
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-builder

WORKDIR /build/frontend

# Install dependencies first (cache layer)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build


# ---------------------------------------------------------------------------
# Stage 2: Production runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# System dependencies: supervisor, curl, git for health checks, cloning, and OpenCode download
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        supervisor \
        curl \
        git \
        unzip \
        git \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI — needed for PR creation by remediation agent
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends gh && \
    rm -rf /var/lib/apt/lists/*

# Install uv for fast Python dependency management
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy version file first (needed by install script)
COPY .opencode-version ./

# Copy and run OpenCode install script (non-fatal if download fails)
COPY scripts/install-opencode.sh ./scripts/
ENV OPENSEC_BIN_DIR=/app/bin
RUN bash scripts/install-opencode.sh || echo "WARNING: OpenCode download failed — engine will be unavailable"

# Install Python dependencies (cache layer)
COPY backend/pyproject.toml backend/uv.lock* ./backend/
RUN cd backend && uv sync --frozen --no-dev --no-install-project

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend from stage 1
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

# Copy OpenCode project config and agent definitions
COPY opencode.json ./
COPY .opencode/ ./.opencode/

# Copy supervisor and entrypoint configs
COPY docker/supervisord.conf /etc/supervisor/conf.d/opensec.conf
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# ---------------------------------------------------------------------------
# Environment defaults
# ---------------------------------------------------------------------------
ENV OPENSEC_APP_HOST=0.0.0.0 \
    OPENSEC_APP_PORT=8000 \
    OPENSEC_OPENCODE_HOST=127.0.0.1 \
    OPENSEC_OPENCODE_PORT=4096 \
    OPENSEC_OPENCODE_BIN=/app/bin/opencode \
    OPENSEC_DATA_DIR=/data

# Persistent data volume
VOLUME ["/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
