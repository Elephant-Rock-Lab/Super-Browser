"""Tests for CredentialVault — encrypted credential storage (M39).

Test IDs: TEST-13-01-01 through TEST-13-01-05
Hard boundary HB-13-01: Fernet encryption required, no plaintext storage.
"""

import logging

import pytest

from super_browser.security.credential_vault import CredentialVault


@pytest.fixture
def vault(tmp_path):
    """Return a CredentialVault using a temporary directory."""
    vault_dir = tmp_path / "vault"
    key_file = tmp_path / ".vault_key"
    return CredentialVault(vault_dir=vault_dir, key_file=key_file)


# -- TEST-13-01-01: Store + retrieve roundtrip --------------------------------


class TestStoreRetrieveRoundtrip:
    """TEST-13-01-01: Store and retrieve credential roundtrip."""

    def test_store_and_retrieve(self, vault):
        vault.store("example.com", "alice", "s3cret_password!")
        username, password = vault.retrieve("example.com")
        assert username == "alice"
        assert password == "s3cret_password!"

    def test_multiple_sites(self, vault):
        vault.store("site-a.com", "user_a", "pass_a")
        vault.store("site-b.org", "user_b", "pass_b")

        u1, p1 = vault.retrieve("site-a.com")
        assert (u1, p1) == ("user_a", "pass_a")

        u2, p2 = vault.retrieve("site-b.org")
        assert (u2, p2) == ("user_b", "pass_b")

    def test_retrieve_nonexistent_raises(self, vault):
        with pytest.raises(FileNotFoundError, match="missing.dev"):
            vault.retrieve("missing.dev")


# -- TEST-13-01-02: File content is not plaintext -----------------------------


class TestEncryptionAtRest:
    """TEST-13-01-02: File content is not plaintext (HB-13-01)."""

    def test_password_not_in_file_bytes(self, vault):
        plaintext_password = "myPlaintextP@ss"
        vault.store("secure.io", "bob", plaintext_password)

        enc_file = vault._vault_dir / "secure.io.enc"
        raw = enc_file.read_bytes()

        assert plaintext_password.encode("utf-8") not in raw
        assert b"bob" not in raw

    def test_file_is_binary_not_json(self, vault):
        vault.store("test.net", "user", "pwd")
        enc_file = vault._vault_dir / "test.net.enc"
        raw = enc_file.read_bytes()

        # JSON starts with '{' — encrypted content should not
        assert not raw.startswith(b"{")
        assert not raw.startswith(b'"')


# -- TEST-13-01-03: List sites returns entries ---------------------------------


class TestListSites:
    """TEST-13-01-03: List stored sites returns correct entries."""

    def test_empty_vault(self, vault):
        assert vault.list_sites() == []

    def test_returns_sorted_site_names(self, vault):
        vault.store("delta.com", "d", "d_pass")
        vault.store("alpha.com", "a", "a_pass")
        vault.store("charlie.com", "c", "c_pass")

        sites = vault.list_sites()
        assert sites == ["alpha.com", "charlie.com", "delta.com"]


# -- TEST-13-01-04: Delete removes file ---------------------------------------


class TestDelete:
    """TEST-13-01-04: Delete removes credential file."""

    def test_delete_removes_file(self, vault):
        vault.store("temp.io", "tmp_user", "tmp_pass")
        assert "temp.io" in vault.list_sites()

        vault.delete("temp.io")
        assert "temp.io" not in vault.list_sites()

    def test_delete_nonexistent_raises(self, vault):
        with pytest.raises(FileNotFoundError):
            vault.delete("ghost.xyz")

    def test_delete_one_preserves_others(self, vault):
        vault.store("keep.com", "k", "k_pass")
        vault.store("remove.com", "r", "r_pass")

        vault.delete("remove.com")
        assert "keep.com" in vault.list_sites()
        assert "remove.com" not in vault.list_sites()


# -- TEST-13-01-05: No credentials in log output ------------------------------


class TestCredentialLogging:
    """TEST-13-01-05: Credentials never appear in log output."""

    def test_no_credentials_in_logs(self, vault, caplog):
        with caplog.at_level(logging.DEBUG, logger="super_browser.security.credential_vault"):
            vault.store("logtest.com", "loguser", "super_secret_123")
            vault.retrieve("logtest.com")
            vault.delete("logtest.com")

        for record in caplog.records:
            msg = record.message
            assert "super_secret_123" not in msg
            assert "loguser" not in msg
