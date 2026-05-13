"""TEST-09-02: Fail-fast without LLM client (H5)."""

import asyncio
import subprocess
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from super_browser.agent.facade import ConfigurationError, SuperBrowser


def _make_browser_without_llm():
    """Create a SuperBrowser with no LLM client configured."""
    browser = SuperBrowser()
    browser._session = MagicMock()
    browser._page = MagicMock()
    browser._page.url = "https://example.com"
    browser._page.title = AsyncMock(return_value="Test Page")
    browser._controller = MagicMock()
    browser._running = True
    # Explicitly ensure no LLM client
    browser._llm_client = None
    return browser


class TestActRaisesConfigurationError:
    """TEST-09-02-01: act() without LLM raises ConfigurationError."""

    def test_raises_configuration_error(self):
        async def _test():
            browser = _make_browser_without_llm()
            with pytest.raises(ConfigurationError):
                await browser.act("click the button")
        asyncio.run(_test())


class TestErrorMessageContainsSubstring:
    """TEST-09-02-02: Error message contains 'llm_client' substring."""

    def test_error_message_mentions_llm_client(self):
        async def _test():
            browser = _make_browser_without_llm()
            with pytest.raises(ConfigurationError) as exc_info:
                await browser.act("do something")
            assert "llm_client" in str(exc_info.value)
        asyncio.run(_test())


class TestNoNoOpLLMInSource:
    """TEST-09-02-03: grep -r '_NoOpLLM' src/ returns 0 matches."""

    def test_no_noop_llm_in_source(self):
        """Verify no _NoOpLLM references exist in the source tree."""
        result = subprocess.run(
            [sys.executable, "-c",
             "import subprocess; r = subprocess.run(['grep', '-r', '_NoOpLLM', 'src/'], "
             "capture_output=True, text=True); print(r.returncode)"],
            capture_output=True, text=True,
            cwd="C:/Next AI/SUPER-BROWSER",
        )
        # grep returns 1 when no matches found (which is what we want)
        output = result.stdout.strip()
        assert output == "1", "_NoOpLLM found in source tree"
