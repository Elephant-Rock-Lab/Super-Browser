"""Tests for SecretRedactor."""

from pathlib import Path

from super_browser.security.redactor import SecretRedactor
from super_browser.security.types import RedactionResult, SecretType, SecurityConfig


def _redactor(**kwargs) -> SecretRedactor:
    config = SecurityConfig(**kwargs)
    return SecretRedactor(config)


class TestAnthropicKey:
    def test_detects_anthropic(self):
        r = _redactor()
        result = r.redact("key=sk-ant-api03-abc123def456ghi789")
        assert result.was_redacted is True
        assert "sk-ant-api03" not in result.redacted_text
        assert "[REDACTED:anthropic_key:" in result.redacted_text


class TestOpenRouterKey:
    def test_detects_openrouter(self):
        r = _redactor()
        result = r.redact("key=sk-or-v1-abcdef123456")
        assert result.was_redacted is True
        assert "[REDACTED:openrouter_key:" in result.redacted_text


class TestOpenAIKey:
    def test_detects_openai(self):
        r = _redactor()
        result = r.redact("key=sk-abcdefghijklmnopqrstuvwxyz")
        assert result.was_redacted is True


class TestGitHubToken:
    def test_detects_github_pat(self):
        r = _redactor()
        result = r.redact("token=ghp_" + "a" * 36)
        assert result.was_redacted is True
        assert "[REDACTED:github_token:" in result.redacted_text


class TestAWSKey:
    def test_detects_aws_access_key(self):
        r = _redactor()
        result = r.redact("key=AKIA" + "A" * 16)
        assert result.was_redacted is True


class TestGoogleKey:
    def test_detects_google_api(self):
        r = _redactor()
        result = r.redact("key=AIza" + "a" * 35)
        assert result.was_redacted is True


class TestSlackToken:
    def test_detects_slack_bot(self):
        r = _redactor()
        result = r.redact("token=xoxb-abc-123-def")
        assert result.was_redacted is True


class TestStripeKey:
    def test_detects_stripe_secret(self):
        r = _redactor()
        result = r.redact("key=sk_live_" + "a" * 24)
        assert result.was_redacted is True


class TestPassword:
    def test_detects_password(self):
        r = _redactor()
        result = r.redact('password=mysecret123')
        assert result.was_redacted is True
        assert "mysecret123" not in result.redacted_text


class TestPEMKey:
    def test_detects_rsa_private(self):
        r = _redactor()
        result = r.redact("-----BEGIN RSA PRIVATE KEY-----\nMIIE...")
        assert result.was_redacted is True
        assert "[REDACTED:pem_key:" in result.redacted_text

    def test_detects_ec_private(self):
        r = _redactor()
        result = r.redact("-----BEGIN EC PRIVATE KEY-----\nabc...")
        assert result.was_redacted is True


class TestJWT:
    def test_detects_jwt(self):
        r = _redactor()
        result = r.redact("token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.abc123def456")
        assert result.was_redacted is True


class TestDatabaseURL:
    def test_detects_postgres(self):
        r = _redactor()
        result = r.redact("db=postgresql://user:pass@host:5432/db")
        assert result.was_redacted is True

    def test_detects_mysql(self):
        r = _redactor()
        result = r.redact("db=mysql://user:pass@host:3306/db")
        assert result.was_redacted is True

    def test_detects_redis(self):
        r = _redactor()
        result = r.redact("cache=redis://localhost:6379/0")
        assert result.was_redacted is True


class TestCleanText:
    def test_no_secrets(self):
        r = _redactor()
        result = r.redact("The quick brown fox jumps over the lazy dog.")
        assert result.was_redacted is False
        assert result.redaction_count == 0


class TestCustomPatterns:
    def test_custom_pattern(self):
        r = _redactor(custom_secret_patterns=[("my_token", r"MY_SECRET_\w+")])
        result = r.redact("token=MY_SECRET_abc123")
        assert result.was_redacted is True
        assert "MY_SECRET_abc123" not in result.redacted_text


class TestPlaceholderFormat:
    def test_contains_type_and_hash(self):
        r = _redactor()
        result = r.redact("key=sk-ant-api03-abc123def456ghi789")
        assert len(result.entries) > 0
        entry = result.entries[0]
        assert entry.secret_type == SecretType.ANTHROPIC_KEY
        assert len(entry.sha256_hash6) == 6
        assert entry.placeholder.startswith("[REDACTED:anthropic_key:")
        assert entry.placeholder.endswith("]")


class TestAuditLog:
    def test_log_written(self, tmp_path):
        log_path = str(tmp_path / "audit.log")
        r = _redactor(redaction_log_path=log_path)
        r.redact("key=sk-ant-api03-abc123def456ghi789")
        content = Path(log_path).read_text(encoding="utf-8")
        assert "anthropic_key" in content
        assert "sk-ant-api03" not in content

    def test_no_log_without_path(self):
        r = _redactor()
        result = r.redact("key=sk-ant-api03-abc123def456ghi789")
        assert result.was_redacted is True


class TestPerformance:
    def test_large_text_fast(self):
        r = _redactor()
        text = "Normal safe text " * 1000
        result = r.redact(text)
        assert result.scan_time_ms < 100.0


class TestPatternCount:
    def test_has_patterns(self):
        r = _redactor()
        assert r.pattern_count >= 20


class TestMultipleSecrets:
    def test_redacts_multiple(self):
        r = _redactor()
        text = "key=sk-ant-api03-abc AND token=ghp_" + "a" * 36
        result = r.redact(text)
        assert result.was_redacted is True
        assert result.redaction_count >= 2
