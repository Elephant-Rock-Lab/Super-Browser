"""CredentialVault — encrypted local credential storage for site logins.

Uses Fernet symmetric encryption (cryptography library) to store credentials
at rest.  The encryption key is derived from a machine-specific identifier
and cached at ``~/.config/super-browser/.vault_key``.

Hard boundary HB-13-01: Credentials are ALWAYS encrypted at rest.
Credential values are NEVER logged.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import platform
import uuid
from pathlib import Path
from typing import Optional

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

_DEFAULT_VAULT_DIR = Path.home() / ".config" / "super-browser" / "vault"
_DEFAULT_KEY_FILE = Path.home() / ".config" / "super-browser" / ".vault_key"


def _get_machine_id() -> str:
    """Return a machine-specific identifier for key derivation.

    Tries ``/etc/machine-id`` on Linux, falls back to a composite of
    platform details.  On Windows/macOS the composite is always used.
    """
    # Try Linux machine-id first
    machine_id_path = Path("/etc/machine-id")
    if machine_id_path.exists():
        return machine_id_path.read_text().strip()

    # Fallback: composite identifier
    parts = [
        platform.node(),
        platform.system(),
        platform.machine(),
        str(uuid.getnode()),
    ]
    return "|".join(parts)


def _derive_key(machine_id: str) -> bytes:
    """Derive a 32-byte Fernet key from *machine_id* using SHA-256."""
    digest = hashlib.sha256(machine_id.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _load_or_create_key(key_file: Path) -> bytes:
    """Load an existing vault key or create and persist a new one."""
    if key_file.exists():
        raw = key_file.read_bytes()
        # Validate it's a proper Fernet key
        try:
            Fernet(raw)
            return raw
        except Exception:
            logger.warning("Invalid vault key file, regenerating")

    # Generate a deterministic key from machine ID
    machine_id = _get_machine_id()
    key = _derive_key(machine_id)

    # Persist for cross-session stability
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_bytes(key)
    # Restrict permissions (best-effort on Windows)
    try:
        os.chmod(key_file, 0o600)
    except OSError:
        pass

    return key


class CredentialVault:
    """Encrypted local credential storage.

    Each site's credentials are stored as a separate encrypted file under
    ``<vault_dir>/<site>.enc``.  Values are encrypted with Fernet (AES-128-CBC
    with HMAC-SHA256 authentication).

    Parameters
    ----------
    vault_dir:
        Directory for encrypted credential files.
    key_file:
        Path to the vault encryption key.  If ``None``, uses the default.
    """

    def __init__(
        self,
        vault_dir: Optional[Path] = None,
        key_file: Optional[Path] = None,
    ) -> None:
        self._vault_dir = vault_dir or _DEFAULT_VAULT_DIR
        self._key_file = key_file or _DEFAULT_KEY_FILE
        self._fernet: Optional[Fernet] = None

    @property
    def _cipher(self) -> Fernet:
        """Lazy-initialised Fernet cipher."""
        if Fernet is None:
            raise ImportError(
                "cryptography is required for CredentialVault. "
                "Install it with: pip install superbrowser-sdk[security]"
            )
        if self._fernet is None:
            key = _load_or_create_key(self._key_file)
            self._fernet = Fernet(key)
        return self._fernet

    # -- Public API --------------------------------------------------------

    def store(self, site: str, username: str, password: str) -> Path:
        """Encrypt and store credentials for *site*.

        Parameters
        ----------
        site:
            Site identifier (e.g. ``"example.com"``).
        username:
            Login username.
        password:
            Login password.

        Returns
        -------
        Path
            Path to the encrypted credential file.
        """
        self._vault_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"username": username, "password": password})
        encrypted = self._cipher.encrypt(payload.encode("utf-8"))
        enc_path = self._vault_dir / f"{site}.enc"
        enc_path.write_bytes(encrypted)
        logger.info("Credential stored for site: %s", site)
        return enc_path

    def retrieve(self, site: str) -> tuple[str, str]:
        """Decrypt and return credentials for *site*.

        Parameters
        ----------
        site:
            Site identifier.

        Returns
        -------
        tuple[str, str]
            ``(username, password)``.

        Raises
        ------
        FileNotFoundError
            If no credential file exists for *site*.
        """
        enc_path = self._vault_dir / f"{site}.enc"
        if not enc_path.exists():
            raise FileNotFoundError(f"No credentials stored for site: {site}")

        encrypted = enc_path.read_bytes()
        decrypted = self._cipher.decrypt(encrypted)
        data = json.loads(decrypted.decode("utf-8"))
        return data["username"], data["password"]

    def list_sites(self) -> list[str]:
        """Return a sorted list of all stored site identifiers."""
        if not self._vault_dir.exists():
            return []
        sites = [p.stem for p in self._vault_dir.glob("*.enc")]
        return sorted(sites)

    def delete(self, site: str) -> None:
        """Remove stored credentials for *site*.

        Parameters
        ----------
        site:
            Site identifier.

        Raises
        ------
        FileNotFoundError
            If no credential file exists for *site*.
        """
        enc_path = self._vault_dir / f"{site}.enc"
        if not enc_path.exists():
            raise FileNotFoundError(f"No credentials stored for site: {site}")
        enc_path.unlink()
        logger.info("Credential deleted for site: %s", site)
