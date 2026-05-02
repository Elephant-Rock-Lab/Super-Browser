"""TEST-07-01-06: TLS JA4 fingerprint must match the Chrome 143 profile.

If the ``httpmorph`` library is installed, this test verifies that its
default JA4 fingerprint string matches the expected Chrome 143 profile.
If ``httpmorph`` is not available the test is **skipped** (not failed),
because the library is an optional dependency.
"""

import pytest


pytestmark = pytest.mark.integration

# The expected JA4 fingerprint prefix for Chrome 143 on macOS.
# Reference: https://github.com/nickelc/httpmorph/blob/main/profiles/chrome143.json
_CHROME_143_JA4_PREFIX = "t13d1516h2"


@pytest.mark.asyncio
async def test_tls_ja4_matches_chrome_143():
    """JA4 fingerprint from httpmorph must match Chrome 143 profile."""
    try:
        from httpmorph import Client  # noqa: F401
    except ImportError:
        pytest.skip("httpmorph not installed")

    try:
        from httpmorph.profiles import get_profile
    except ImportError:
        pytest.skip("httpmorph.profiles not available")

    profile = get_profile("chrome143")
    ja4 = getattr(profile, "ja4", None) or profile.get("ja4")
    assert ja4 is not None, "httpmorph chrome143 profile has no ja4 field"
    assert ja4.startswith(_CHROME_143_JA4_PREFIX), (
        f"JA4 fingerprint {ja4!r} does not match Chrome 143 prefix "
        f"{_CHROME_143_JA4_PREFIX!r}"
    )
