#!/usr/bin/env bash
# install-scanners.sh — fetch & verify pinned Trivy + Semgrep binaries (ADR-0028).
#
# Reads `.scanner-versions` for the pinned <name> <version> <sha256> tuples and
# stages each binary into `bin/<name>`. SHA256 is checked against the recorded
# value; a mismatch aborts unless OPENSEC_SCANNER_VERIFY=warn is set (intended
# only for local development where the user has rebuilt a binary).
#
# Layout:
#   bin/trivy     — extracted Trivy binary (chmod +x)
#   bin/semgrep   — extracted Semgrep binary (chmod +x)
#
# This script is intentionally simple: it shells out to curl + tar / unzip and
# does not rely on docker. Run it once at image-build time; the runtime
# `SubprocessScannerRunner` uses `verify_scanner_checksums()` to re-check on
# every assessment.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSIONS_FILE="${REPO_ROOT}/.scanner-versions"
BIN_DIR="${OPENSEC_BIN_DIR:-${REPO_ROOT}/bin}"
VERIFY_MODE="${OPENSEC_SCANNER_VERIFY:-strict}"

if [[ ! -f "${VERSIONS_FILE}" ]]; then
  echo "error: ${VERSIONS_FILE} not found" >&2
  exit 1
fi
mkdir -p "${BIN_DIR}"

case "$(uname -s)" in
  Linux*)  OS="Linux";  OS_LC="linux"  ;;
  Darwin*) OS="macOS";  OS_LC="darwin" ;;
  *) echo "unsupported OS: $(uname -s)" >&2; exit 1 ;;
esac

case "$(uname -m)" in
  x86_64|amd64)  ARCH="64bit";  ARCH_LC="amd64" ;;
  arm64|aarch64) ARCH="ARM64";  ARCH_LC="arm64" ;;
  *) echo "unsupported arch: $(uname -m)" >&2; exit 1 ;;
esac

verify_sha() {
  local file="$1" expected="$2" name="$3"
  local actual
  actual="$(shasum -a 256 "${file}" | awk '{print $1}')"
  if [[ "${actual}" != "${expected}" ]]; then
    if [[ "${VERIFY_MODE}" == "warn" ]]; then
      echo "warn: ${name} sha256 mismatch (expected ${expected}, got ${actual})" >&2
    else
      echo "error: ${name} sha256 mismatch (expected ${expected}, got ${actual})" >&2
      exit 1
    fi
  fi
}

install_trivy() {
  local version="$1" expected_sha="$2"
  local archive="trivy_${version}_${OS}-${ARCH}.tar.gz"
  local url="https://github.com/aquasecurity/trivy/releases/download/v${version}/${archive}"
  local tmp
  tmp="$(mktemp -d)"
  echo "==> downloading ${url}"
  curl -fsSL "${url}" -o "${tmp}/${archive}"
  tar -xzf "${tmp}/${archive}" -C "${tmp}"
  install -m 0755 "${tmp}/trivy" "${BIN_DIR}/trivy"
  verify_sha "${BIN_DIR}/trivy" "${expected_sha}" "trivy"
  rm -rf "${tmp}"
}

install_semgrep() {
  local version="$1" expected_sha="$2"
  # Semgrep is published on PyPI; we install into a private prefix and copy
  # the launcher into bin/. This keeps the runtime contract identical to
  # Trivy (one executable on disk under bin/).
  local prefix
  prefix="${REPO_ROOT}/.semgrep-${version}"
  python3 -m venv "${prefix}"
  "${prefix}/bin/pip" install --quiet "semgrep==${version}"
  install -m 0755 "${prefix}/bin/semgrep" "${BIN_DIR}/semgrep"
  verify_sha "${BIN_DIR}/semgrep" "${expected_sha}" "semgrep"
}

while read -r line; do
  # Trim comments and blank lines.
  line="${line%%#*}"
  line="$(echo "${line}" | xargs)"
  [[ -z "${line}" ]] && continue
  read -r name version sha <<<"${line}"
  case "${name}" in
    trivy)   install_trivy   "${version}" "${sha}" ;;
    semgrep) install_semgrep "${version}" "${sha}" ;;
    *) echo "unknown scanner ${name}" >&2; exit 1 ;;
  esac
done < "${VERSIONS_FILE}"

echo "==> scanners installed at ${BIN_DIR}"
