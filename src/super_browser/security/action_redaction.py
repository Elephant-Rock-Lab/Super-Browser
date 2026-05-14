"""ActionResult redaction pipeline — wires SecretRedactor into result serialization."""
from __future__ import annotations

import copy
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from super_browser.security.redactor import SecretRedactor
from super_browser.security.types import SecurityConfig

# Keys that trigger value redaction regardless of value content
_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "pass",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "api-key",
        "secret",
        "secret_key",
        "secretkey",
        "client_secret",
        "auth",
        "authorization",
        "credential",
        "credentials",
        "private_key",
        "privatekey",
        "cookie",
        "cookies",
        "session_id",
        "sessionid",
        "proxy",
        "proxy_password",
    }
)

_default_redactor: Optional[SecretRedactor] = None


def configure_redaction(config: SecurityConfig) -> None:
    """Configure the default redactor for ActionResult.to_dict()."""
    global _default_redactor
    _default_redactor = SecretRedactor(config)


def is_redaction_configured() -> bool:
    return _default_redactor is not None


def redact_args(args: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive values in an arguments dict.

    Two-pass algorithm:
    1. Key-name matching against _SENSITIVE_KEYS
    2. Value-pattern matching via SecretRedactor (if configured)
    """
    result = copy.deepcopy(args)
    _redact_dict_recursive(result)
    return result


def _redact_dict_recursive(d: dict[str, Any]) -> None:
    """Recursively redact sensitive keys in a dict (in-place)."""
    for key in list(d.keys()):
        key_lower = key.lower().replace("-", "_")
        if key_lower in _SENSITIVE_KEYS:
            d[key] = f"[REDACTED:{key}]"
        elif isinstance(d[key], dict):
            _redact_dict_recursive(d[key])
        elif isinstance(d[key], str) and _default_redactor is not None:
            redacted = _default_redactor.redact(d[key])
            if redacted.was_redacted:
                d[key] = redacted.redacted_text


def redact_context(url: str) -> str:
    """Scrub sensitive query parameters from a URL.

    Standalone URL scrub — does NOT delegate to SecretRedactor.
    """
    parsed = urlparse(url)
    if not parsed.query:
        return url

    params = parse_qs(parsed.query, keep_blank_values=True)
    redacted = False
    new_params: dict[str, list[str]] = {}
    for key, values in params.items():
        key_lower = key.lower().replace("-", "_")
        if key_lower in _SENSITIVE_KEYS:
            new_params[key] = ["[REDACTED:query_param]"]
            redacted = True
        else:
            new_params[key] = values

    if not redacted:
        return url

    new_query = urlencode(new_params, doseq=True, safe="[]:")
    return urlunparse(parsed._replace(query=new_query))


def redact_result_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Redact an ActionResult.to_dict() output."""
    if _default_redactor is None:
        return d

    result = copy.deepcopy(d)

    # Redact 'data' field if it's a dict
    if isinstance(result.get("data"), dict):
        _redact_dict_recursive(result["data"])

    # Redact 'error' message
    if isinstance(result.get("error"), dict):
        error_msg = result["error"].get("message", "")
        if error_msg:
            redacted = _default_redactor.redact(error_msg)
            if redacted.was_redacted:
                result["error"]["message"] = redacted.redacted_text

    return result
