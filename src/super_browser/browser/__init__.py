"""GAP-01: Browser Session & CDP Integration."""

from super_browser.browser.config import SessionConfig, SessionMode
from super_browser.browser.session import BrowserSession, BrowserState
from super_browser.browser.cdp import CDPBridge, CDPResult
from super_browser.browser.page import PageHandle
from super_browser.browser.discovery import BrowserDiscovery, DiscoveryResult
from super_browser.browser.shutdown import ShutdownSupervisor

__all__ = [
    "BrowserDiscovery", "BrowserSession", "BrowserState",
    "CDPBridge", "CDPResult", "DiscoveryResult",
    "PageHandle", "SessionConfig", "SessionMode",
    "ShutdownSupervisor",
]
