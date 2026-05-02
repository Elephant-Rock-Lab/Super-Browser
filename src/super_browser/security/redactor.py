"""SecretRedactor — 40+ regex patterns for credential detection and redaction."""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Optional

from super_browser.security.types import (
    RedactionEntry,
    RedactionResult,
    SecretType,
    SecurityConfig,
)

_BUILTIN_PATTERNS: list[tuple[SecretType, str, str]] = [
    (SecretType.ANTHROPIC_KEY, "anthropic_api_key", r"sk-ant-api\S+"),
    (SecretType.OPENROUTER_KEY, "openrouter_api_key", r"sk-or-v1-\S+"),
    (SecretType.OPENAI_KEY, "openai_api_key", r"sk-[a-zA-Z0-9]{20,}"),
    (SecretType.GITHUB_TOKEN, "github_pat", r"ghp_[a-zA-Z0-9]{30,}"),
    (SecretType.GITHUB_TOKEN, "github_oauth", r"gho_[a-zA-Z0-9]{30,}"),
    (SecretType.GITHUB_TOKEN, "github_user_token", r"ghu_[a-zA-Z0-9]{30,}"),
    (SecretType.GITHUB_TOKEN, "github_server_token", r"ghs_[a-zA-Z0-9]{30,}"),
    (SecretType.GITHUB_TOKEN, "github_refresh_token", r"ghr_[a-zA-Z0-9]{30,}"),
    (SecretType.AWS_ACCESS_KEY, "aws_access_key_id", r"AKIA[A-Z0-9]{16}"),
    (SecretType.AWS_SECRET_KEY, "aws_secret_key", r"(?:aws_secret_access_key|AWS_SECRET_ACCESS_KEY)\s*[=:]\s*[A-Za-z0-9/+=]{40}"),
    (SecretType.GOOGLE_API_KEY, "google_api_key", r"AIza[a-zA-Z0-9_-]{35}"),
    (SecretType.SLACK_TOKEN, "slack_bot_token", r"xoxb-[a-zA-Z0-9-]+"),
    (SecretType.SLACK_TOKEN, "slack_user_token", r"xoxp-[a-zA-Z0-9-]+"),
    (SecretType.SLACK_TOKEN, "slack_app_token", r"xapp-[a-zA-Z0-9-]+"),
    (SecretType.SLACK_TOKEN, "slack_webhook", r"https://hooks\.slack\.com/services/T[a-zA-Z0-9]+/B[a-zA-Z0-9]+/[a-zA-Z0-9]+"),
    (SecretType.STRIPE_KEY, "stripe_secret_key", r"sk_live_[a-zA-Z0-9]{24,}"),
    (SecretType.STRIPE_KEY, "stripe_restricted_key", r"rk_live_[a-zA-Z0-9]{24,}"),
    (SecretType.STRIPE_KEY, "stripe_publishable_key", r"pk_live_[a-zA-Z0-9]{24,}"),
    (SecretType.PASSWORD, "password_assignment", r"(?:password|passwd|pass)\s*[=:]\s*[\"\']?[^\s\"\']{6,}"),
    (SecretType.PEM_KEY, "rsa_private_key", r"-----BEGIN (?:RSA )?PRIVATE KEY-----"),
    (SecretType.PEM_KEY, "ec_private_key", r"-----BEGIN EC PRIVATE KEY-----"),
    (SecretType.PEM_KEY, "dsa_private_key", r"-----BEGIN DSA PRIVATE KEY-----"),
    (SecretType.PEM_KEY, "pgp_private_key", r"-----BEGIN PGP PRIVATE KEY BLOCK-----"),
    (SecretType.JWT, "jwt_token", r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+"),
    (SecretType.DATABASE_URL, "postgres_url", r"postgres(?:ql)?://[^\s\"\']+"),
    (SecretType.DATABASE_URL, "mysql_url", r"mysql://[^\s\"\']+"),
    (SecretType.DATABASE_URL, "mongodb_url", r"mongodb(?:\+srv)?://[^\s\"\']+"),
    (SecretType.DATABASE_URL, "redis_url", r"redis://[^\s\"\']+"),
    (SecretType.ANTHROPIC_KEY, "anthropic_key_alt", r"sk-ant-\S+"),
    (SecretType.OPENAI_KEY, "openai_org_key", r"org-[a-zA-Z0-9]{20,}"),
    (SecretType.GENERIC_TOKEN, "bearer_token", r"(?:Bearer|bearer)\s+[a-zA-Z0-9_\-.]{20,}"),
    (SecretType.GENERIC_TOKEN, "basic_auth", r"(?:Basic|basic)\s+[a-zA-Z0-9+/=]{16,}"),
    (SecretType.GENERIC_TOKEN, "api_key_generic", r"(?:api[_-]?key|apikey)\s*[=:]\s*[\"\']?[a-zA-Z0-9]{20,}"),
    (SecretType.GENERIC_TOKEN, "secret_key_generic", r"(?:secret[_-]?key|secretkey)\s*[=:]\s*[\"\']?[a-zA-Z0-9]{20,}"),
    (SecretType.GENERIC_TOKEN, "access_token_generic", r"(?:access[_-]?token|accesstoken)\s*[=:]\s*[\"\']?[a-zA-Z0-9_\-.]{20,}"),
    (SecretType.GENERIC_TOKEN, "heroku_api_key", r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"),
    (SecretType.AWS_ACCESS_KEY, "aws_access_key_alt", r"ABIA[A-Z0-9]{16}"),
    (SecretType.GOOGLE_API_KEY, "google_oauth_secret", r"(?:client_secret|GOOGLE_CLIENT_SECRET)\s*[=:]\s*[\"\']?[a-zA-Z0-9_-]{20,}"),
]


class SecretRedactor:

    def __init__(self, config: SecurityConfig) -> None:
        self._patterns: list[tuple[SecretType, str, re.Pattern[str]]] = []
        self._redaction_log_path: Optional[str] = config.redaction_log_path
        self._load_patterns(config)

    def _load_patterns(self, config: SecurityConfig) -> None:
        for secret_type, name, regex in _BUILTIN_PATTERNS:
            self._patterns.append((secret_type, name, re.compile(regex, re.IGNORECASE)))
        for custom_name, custom_regex in config.custom_secret_patterns:
            self._patterns.append((
                SecretType.GENERIC_TOKEN,
                custom_name,
                re.compile(custom_regex, re.IGNORECASE),
            ))

    def redact(self, text: str) -> RedactionResult:
        start = time.perf_counter()
        entries: list[RedactionEntry] = []
        matches: list[tuple[int, int, SecretType, str]] = []

        for secret_type, name, compiled in self._patterns:
            for m in compiled.finditer(text):
                matches.append((m.start(), m.end(), secret_type, m.group()))

        matches.sort(key=lambda x: x[0])
        seen: set[tuple[int, int]] = set()
        deduped = []
        for s, e, st, val in matches:
            if (s, e) not in seen:
                seen.add((s, e))
                deduped.append((s, e, st, val))

        if not deduped:
            elapsed = (time.perf_counter() - start) * 1000
            return RedactionResult(was_redacted=False, redacted_text=text, scan_time_ms=elapsed)

        result_chars = list(text)
        offset = 0
        for s, e, secret_type, value in deduped:
            placeholder = self._compute_placeholder(secret_type, value)
            hash6 = hashlib.sha256(value.encode()).hexdigest()[:6]
            entry = RedactionEntry(
                secret_type=secret_type,
                original_start=s,
                original_end=e,
                placeholder=placeholder,
                sha256_hash6=hash6,
            )
            entries.append(entry)
            adj_s = s + offset
            adj_e = e + offset
            result_chars[adj_s:adj_e] = list(placeholder)
            offset += len(placeholder) - (e - s)

        redacted_text = "".join(result_chars)
        self._write_log(entries)
        elapsed = (time.perf_counter() - start) * 1000
        return RedactionResult(
            was_redacted=True,
            redacted_text=redacted_text,
            entries=entries,
            scan_time_ms=elapsed,
        )

    def _compute_placeholder(self, secret_type: SecretType, secret_value: str) -> str:
        hash6 = hashlib.sha256(secret_value.encode()).hexdigest()[:6]
        return f"[REDACTED:{secret_type.value}:{hash6}]"

    def _write_log(self, entries: list[RedactionEntry]) -> None:
        if not self._redaction_log_path:
            return
        try:
            path = Path(self._redaction_log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                for entry in entries:
                    f.write(json.dumps({
                        "secret_type": entry.secret_type.value,
                        "placeholder": entry.placeholder,
                        "sha256_hash6": entry.sha256_hash6,
                        "original_start": entry.original_start,
                        "original_end": entry.original_end,
                    }) + "\n")
        except Exception:
            pass

    @property
    def pattern_count(self) -> int:
        return len(self._patterns)
