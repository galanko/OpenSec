"""Credential Vault — AES-256-GCM encrypted secret storage (ADR-0016).

Encryption key resolution priority:
1. System keyring (macOS Keychain, GNOME Keyring, Windows Credential Manager)
2. OPENSEC_CREDENTIAL_KEY environment variable (base64-encoded 32 bytes)
3. Raises CredentialKeyError — UI layer must prompt user to configure a key

Credentials are encrypted per-value with random 12-byte IVs and stored in the
``credential`` table. The vault never exposes plaintext via API — only internal
methods (workspace config generation) can decrypt.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from opensec.db import repo_credential

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger(__name__)

_KEYRING_SERVICE = "opensec"
_KEYRING_USERNAME = "credential-vault-key"
_KEY_LENGTH = 32  # AES-256


class CredentialKeyError(Exception):
    """Raised when no encryption key can be resolved."""


# ---------------------------------------------------------------------------
# Low-level crypto helpers
# ---------------------------------------------------------------------------


def _encrypt(key: bytes, plaintext: str) -> tuple[bytes, bytes]:
    """Encrypt *plaintext* with AES-256-GCM. Returns (ciphertext, iv)."""
    iv = os.urandom(12)  # 96-bit IV recommended for GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    return ciphertext, iv


def _decrypt(key: bytes, ciphertext: bytes, iv: bytes) -> str:
    """Decrypt *ciphertext* with AES-256-GCM. Returns plaintext string."""
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(iv, ciphertext, None).decode("utf-8")


# ---------------------------------------------------------------------------
# Key resolution
# ---------------------------------------------------------------------------


def _try_keyring() -> bytes | None:
    """Attempt to load or generate a key from the system keyring."""
    try:
        import keyring as kr  # noqa: PLC0415
    except ImportError:
        return None

    try:
        stored = kr.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
        if stored:
            return base64.b64decode(stored)
        # First run — generate and store a random key.
        new_key = os.urandom(_KEY_LENGTH)
        kr.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, base64.b64encode(new_key).decode())
        logger.info("Generated new credential vault key in system keyring")
        return new_key
    except Exception:
        logger.debug("System keyring unavailable", exc_info=True)
        return None


def _try_env_var() -> bytes | None:
    """Read a base64-encoded key from OPENSEC_CREDENTIAL_KEY."""
    raw = os.environ.get("OPENSEC_CREDENTIAL_KEY", "").strip()
    if not raw:
        return None
    key = base64.b64decode(raw)
    if len(key) != _KEY_LENGTH:
        msg = f"OPENSEC_CREDENTIAL_KEY must decode to {_KEY_LENGTH} bytes, got {len(key)}"
        raise CredentialKeyError(msg)
    return key


def resolve_key() -> bytes:
    """Resolve encryption key via priority chain. Raises CredentialKeyError on failure."""
    key = _try_keyring()
    if key is not None:
        return key

    key = _try_env_var()
    if key is not None:
        return key

    msg = (
        "No credential encryption key configured. "
        "Set OPENSEC_CREDENTIAL_KEY (base64-encoded 32 bytes) or install the 'keyring' package."
    )
    raise CredentialKeyError(msg)


# ---------------------------------------------------------------------------
# CredentialVault
# ---------------------------------------------------------------------------


class CredentialVault:
    """Manages encrypted credential storage for integrations."""

    def __init__(self, db: aiosqlite.Connection, key: bytes | None = None) -> None:
        self._db = db
        self._key = key if key is not None else resolve_key()
        if len(self._key) != _KEY_LENGTH:
            msg = f"Encryption key must be {_KEY_LENGTH} bytes, got {len(self._key)}"
            raise CredentialKeyError(msg)

    async def store(self, integration_id: str, key_name: str, plaintext: str) -> str:
        """Encrypt and store a credential. Overwrites if (integration_id, key_name) exists.

        Returns the credential row ID.
        """
        ciphertext, iv = _encrypt(self._key, plaintext)

        existing = await repo_credential.get_credential(self._db, integration_id, key_name)
        if existing:
            await repo_credential.update_credential(
                self._db, integration_id, key_name, ciphertext, iv
            )
            return existing["id"]

        return await repo_credential.create_credential(
            self._db, integration_id, key_name, ciphertext, iv
        )

    async def retrieve(self, integration_id: str, key_name: str) -> str:
        """Decrypt and return a credential value. Raises KeyError if not found."""
        row = await repo_credential.get_credential(self._db, integration_id, key_name)
        if row is None:
            msg = f"No credential '{key_name}' for integration '{integration_id}'"
            raise KeyError(msg)
        return _decrypt(self._key, bytes(row["encrypted_value"]), bytes(row["iv"]))

    async def delete(self, integration_id: str, key_name: str) -> bool:
        """Delete a single credential. Returns True if it existed."""
        return await repo_credential.delete_credential(self._db, integration_id, key_name)

    async def delete_for_integration(self, integration_id: str) -> int:
        """Delete all credentials for an integration. Returns count deleted."""
        return await repo_credential.delete_credentials_for_integration(
            self._db, integration_id
        )

    async def list_keys(self, integration_id: str) -> list[dict]:
        """List credential metadata (key_name, created_at, rotated_at) — no values."""
        return await repo_credential.list_credential_keys(self._db, integration_id)

    async def has_credential(self, integration_id: str, key_name: str) -> bool:
        """Check whether a credential exists."""
        row = await repo_credential.get_credential(self._db, integration_id, key_name)
        return row is not None

    async def rotate(self, integration_id: str, key_name: str, new_plaintext: str) -> None:
        """Re-encrypt a credential with a new value. Raises KeyError if not found."""
        existing = await repo_credential.get_credential(self._db, integration_id, key_name)
        if existing is None:
            msg = f"No credential '{key_name}' for integration '{integration_id}'"
            raise KeyError(msg)
        ciphertext, iv = _encrypt(self._key, new_plaintext)
        await repo_credential.update_credential(
            self._db, integration_id, key_name, ciphertext, iv
        )

    async def get_credentials_for_workspace(self, integration_id: str) -> dict[str, str]:
        """Decrypt all credentials for an integration. Used for workspace config injection."""
        keys = await repo_credential.list_credential_keys(self._db, integration_id)
        result: dict[str, str] = {}
        for key_info in keys:
            result[key_info["key_name"]] = await self.retrieve(integration_id, key_info["key_name"])
        return result
