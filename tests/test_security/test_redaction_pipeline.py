"""BATCH-41/TASK-02 — Secret redaction pipeline tests (TEST-41-02-01 through TEST-41-02-10)."""

from __future__ import annotations

from super_browser.results.types import ActionError, ActionResult, ErrorCategory, ResultMeta
from super_browser.security.action_redaction import (
    configure_redaction,
    redact_args,
    redact_context,
)
from super_browser.security.types import SecurityConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_redactor() -> None:
    """Reset module-level _default_redactor to None."""
    import super_browser.security.action_redaction as _mod

    _mod._default_redactor = None


def _setup_redactor() -> None:
    """Configure a default redactor for tests that need it."""
    _reset_redactor()
    configure_redaction(SecurityConfig())


# ---------------------------------------------------------------------------
# TEST-41-02-01: redact_args masks password values
# ---------------------------------------------------------------------------


def test_41_02_01_redact_args_masks_password():
    result = redact_args({"password": "secret"})
    assert result["password"] == "[REDACTED:password]"


# ---------------------------------------------------------------------------
# TEST-41-02-02: redact_args masks token values
# ---------------------------------------------------------------------------


def test_41_02_02_redact_args_masks_token():
    result = redact_args({"api_key": "sk-123"})
    assert "[REDACTED:" in result["api_key"]


# ---------------------------------------------------------------------------
# TEST-41-02-03: redact_args preserves safe keys
# ---------------------------------------------------------------------------


def test_41_02_03_redact_args_preserves_safe_keys():
    result = redact_args({"username": "alice", "page": 2, "verbose": True})
    assert result["username"] == "alice"
    assert result["page"] == 2
    assert result["verbose"] is True


# ---------------------------------------------------------------------------
# TEST-41-02-04: redact_context scrubs URL query params
# ---------------------------------------------------------------------------


def test_41_02_04_redact_context_scrubs_token_param():
    url = "https://x.com/api?token=abc123"
    result = redact_context(url)
    assert "[REDACTED:query_param]" in result
    assert "abc123" not in result
    assert "x.com" in result


# ---------------------------------------------------------------------------
# TEST-41-02-05: redact_context scrubs multiple params
# ---------------------------------------------------------------------------


def test_41_02_05_redact_context_scrubs_multiple_params():
    url = "https://x.com/api?api_key=AAA&secret=BBB&token=CCC"
    result = redact_context(url)
    assert "AAA" not in result
    assert "BBB" not in result
    assert "CCC" not in result
    # All three sensitive params should be redacted
    assert result.count("[REDACTED:query_param]") == 3


# ---------------------------------------------------------------------------
# TEST-41-02-06: ActionResult.to_dict redacts when configured
# ---------------------------------------------------------------------------


def test_41_02_06_to_dict_redacts_when_configured():
    _setup_redactor()
    result = ActionResult(
        ok=False,
        data={"password": "hunter2", "username": "alice"},
        error=ActionError(category=ErrorCategory.VALIDATION, message="bad input"),
        meta=ResultMeta(trace_id="test", duration_ms=1.0),
    )
    d = result.to_dict()
    assert d["data"]["password"] == "[REDACTED:password]"
    assert d["data"]["username"] == "alice"
    _reset_redactor()


# ---------------------------------------------------------------------------
# TEST-41-02-07: to_dict passes through when not configured
# ---------------------------------------------------------------------------


def test_41_02_07_to_dict_no_redaction_without_config():
    _reset_redactor()
    result = ActionResult(
        ok=True,
        data={"password": "hunter2", "token": "abc"},
        meta=ResultMeta(trace_id="test", duration_ms=1.0),
    )
    d = result.to_dict()
    assert d["data"]["password"] == "hunter2"
    assert d["data"]["token"] == "abc"


# ---------------------------------------------------------------------------
# TEST-41-02-08: redact_args handles nested dicts
# ---------------------------------------------------------------------------


def test_41_02_08_redact_args_nested_dicts():
    result = redact_args({"config": {"token": "x", "name": "ok"}})
    assert result["config"]["token"] == "[REDACTED:token]"
    assert result["config"]["name"] == "ok"


# ---------------------------------------------------------------------------
# TEST-41-02-09: redact_context handles no-query URLs
# ---------------------------------------------------------------------------


def test_41_02_09_redact_context_no_query_params():
    url = "https://x.com/path/to/page"
    result = redact_context(url)
    assert result == url


# ---------------------------------------------------------------------------
# TEST-41-02-10: Redaction is idempotent
# ---------------------------------------------------------------------------


def test_41_02_10_redaction_is_idempotent():
    original = {"password": "secret", "api_key": "sk-123", "name": "test"}
    first = redact_args(original)
    second = redact_args(first)
    assert first == second
    assert first["name"] == "test"
