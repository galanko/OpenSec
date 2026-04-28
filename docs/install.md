# Install OpenSec

OpenSec is shipped as a single, signed Docker image published to the GitHub
Container Registry. The image runs as the non-root user `opensec` (UID
10001) and is multi-arch (`linux/amd64` and `linux/arm64`).

## Prerequisites

- Docker 24+ (or any runtime that speaks the OCI image spec)
- An LLM API key — `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
- (Optional) [`cosign`](https://github.com/sigstore/cosign) and
  [`gh`](https://cli.github.com/) for verifying the image — see
  [verify-release.md](verify-release.md)

## Quick start

```bash
docker run --rm -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -v opensec-data:/data \
  ghcr.io/galanko/opensec:0.1.0-alpha
```

Open <http://localhost:8000>.

> **For production deployments, pin the image by digest, not tag.** Tag
> contents can change in principle (we never republish a released tag,
> but you should not have to trust that). Find the digest under the
> [release page](https://github.com/galanko/OpenSec/releases), or run:
>
> ```bash
> docker buildx imagetools inspect ghcr.io/galanko/opensec:0.1.0-alpha
> ```
>
> then use:
>
> ```bash
> docker run ... ghcr.io/galanko/opensec@sha256:<digest>
> ```

## Docker Compose

The repo ships a ready-to-use compose file:

```bash
curl -fsSL https://raw.githubusercontent.com/galanko/OpenSec/v0.1.0-alpha/docker/docker-compose.yml \
  -o docker-compose.yml

ANTHROPIC_API_KEY=sk-ant-... docker compose up
```

## Configuration

| Environment variable        | Required | Default | What it does                                                  |
|-----------------------------|----------|---------|---------------------------------------------------------------|
| `ANTHROPIC_API_KEY`         | One of   | —       | Claude API key.                                                |
| `OPENAI_API_KEY`            | these    | —       | OpenAI API key.                                                |
| `OPENSEC_APP_PORT`          | no       | `8000`  | Port the FastAPI app binds inside the container.               |
| `OPENSEC_DATA_DIR`          | no       | `/data` | Where SQLite + workspace state live. Always mount this volume. |
| `OPENSEC_CREDENTIAL_KEY`    | no       | —       | Base64-encoded 32-byte AES key for the integration vault.      |
| `OPENSEC_DEMO`              | no       | `false` | Auto-seeds demo findings on first run.                         |

## Persisting data

Always mount a volume at `/data`:

```bash
docker run ... -v opensec-data:/data ghcr.io/galanko/opensec:0.1.0-alpha
```

The container's `opensec` user owns `/data` (UID 10001 / GID 10001). If
you bind-mount a host directory instead of a named volume, make sure the
host directory is owned by 10001:10001:

```bash
mkdir -p /srv/opensec-data
sudo chown -R 10001:10001 /srv/opensec-data
docker run ... -v /srv/opensec-data:/data ghcr.io/galanko/opensec:0.1.0-alpha
```

## Upgrading from the pre-alpha root-owned image

Earlier dev builds ran as root and left `/data` owned by `root:root`.
Migrate the volume in place once:

```bash
docker run --rm --user 0 -v opensec-data:/data alpine \
  chown -R 10001:10001 /data
```

## Verifying the image

The image is signed via Sigstore keyless OIDC and carries SLSA build
provenance + CycloneDX SBOM attestations. See
[verify-release.md](verify-release.md) for copy-paste commands.

## Troubleshooting

- **Container exits with `refusing to run as root`** — the entrypoint
  refuses UID 0 by design. Drop the `--user 0` flag. To migrate an
  old root-owned data volume, see "Upgrading" above.
- **`/health` never reaches 200** — supervisord boots uvicorn within
  ~5s. If it doesn't, check `docker logs <container>`. Most often the
  cause is a missing LLM API key (the app starts in degraded mode but
  `/health` still responds 200 — if that's not happening, file an
  issue).
- **SBOM scanner says the image references unknown components** — the
  CycloneDX SBOM lives at `ghcr.io/galanko/opensec:sha256-<digest>.sbom`
  via Sigstore. Most modern scanners pick it up automatically; if yours
  doesn't, download the SBOM from the GitHub release page.
