"""Tests for HeaderRandomizer (BATCH-12 / TASK-01).

Test IDs:
    TEST-12-01-03 — Headers vary between requests (not identical)
    TEST-12-01-04 — Accept-Language includes realistic locales
    TEST-12-01-05 — Accept-Encoding includes gzip, deflate, br
"""

from super_browser.stealth.headers import HeaderRandomizer


class TestHeadersVaryBetweenRequests:
    """TEST-12-01-03: Headers vary between requests (not identical)."""

    def test_randomize_all_produces_different_dicts_over_many_calls(self):
        """Over 50 calls, the randomised header dicts should not all be
        identical (extremely unlikely with the pool sizes used)."""
        rng = HeaderRandomizer()
        results = [rng.randomize_all() for _ in range(50)]
        # Convert each dict to a tuple of sorted items for comparison
        unique = set(tuple(sorted(d.items())) for d in results)
        assert len(unique) > 1, (
            f"Expected varied headers, but all 50 calls produced identical output: {results[0]}"
        )

    def test_accept_varies(self):
        rng = HeaderRandomizer()
        values = {rng.randomize_accept() for _ in range(50)}
        assert len(values) > 1, "Accept header should vary across calls"

    def test_accept_language_varies(self):
        rng = HeaderRandomizer()
        values = {rng.randomize_accept_language() for _ in range(50)}
        assert len(values) > 1, "Accept-Language header should vary across calls"


_KNOWN_LOCALES = {
    "en-US", "en-GB", "de-DE", "fr-FR", "es-ES", "pt-BR",
    "it-IT", "nl-NL", "pl-PL", "ru-RU", "ja-JP", "zh-CN",
    "ko-KR", "sv-SE", "da-DK",
}


class TestAcceptLanguageRealisticLocales:
    """TEST-12-01-04: Accept-Language includes realistic locales."""

    def test_output_contains_recognised_locale(self):
        """Over 100 calls, every output should start with a known locale."""
        rng = HeaderRandomizer()
        for _ in range(100):
            lang = rng.randomize_accept_language()
            primary = lang.split(",")[0]
            assert primary in _KNOWN_LOCALES, (
                f"Unexpected primary locale: {primary!r}"
            )

    def test_json_accept_mode(self):
        """When is_json=True, Accept should be JSON-oriented."""
        rng = HeaderRandomizer()
        val = rng.randomize_accept(is_json=True)
        assert "application/json" in val


class TestAcceptEncodingIncludesStandard:
    """TEST-12-01-05: Accept-Encoding includes gzip, deflate, br."""

    def test_encoding_contains_gzip(self):
        rng = HeaderRandomizer()
        for _ in range(50):
            enc = rng.randomize_accept_encoding()
            assert "gzip" in enc, f"Missing 'gzip' in Accept-Encoding: {enc!r}"

    def test_encoding_contains_deflate(self):
        rng = HeaderRandomizer()
        for _ in range(50):
            enc = rng.randomize_accept_encoding()
            assert "deflate" in enc, f"Missing 'deflate' in Accept-Encoding: {enc!r}"

    def test_encoding_contains_br(self):
        rng = HeaderRandomizer()
        for _ in range(50):
            enc = rng.randomize_accept_encoding()
            assert "br" in enc, f"Missing 'br' in Accept-Encoding: {enc!r}"

    def test_randomize_all_dict_has_required_keys(self):
        rng = HeaderRandomizer()
        headers = rng.randomize_all()
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "Accept-Encoding" in headers

    def test_seeded_randomizer_is_deterministic(self):
        """Two HeaderRandomizer instances with the same seed must produce
        identical output sequences."""
        r1 = HeaderRandomizer(seed=42)
        r2 = HeaderRandomizer(seed=42)
        for _ in range(20):
            assert r1.randomize_all() == r2.randomize_all()
