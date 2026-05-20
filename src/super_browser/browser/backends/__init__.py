"""Browser backend implementations."""
from super_browser.browser.backends.patchright_backend import (
    PatchrightEngine,
    PatchrightPage,
    PatchrightStealthBridge,
)
from super_browser.browser.backends.playwright_backend import (
    PlaywrightEngine,
    PlaywrightPage,
    PlaywrightStealthBridge,
)
from super_browser.browser.backends.selenium_backend import (
    SeleniumEngine,
    SeleniumPage,
    SeleniumStealthBridge,
)

# CDPDirectBackend requires websockets (optional dependency)
try:
    from super_browser.browser.backends.cdp_backend import (
        CDPDirectEngine,
        CDPDirectPage,
        CDPDirectStealthBridge,
    )
except ImportError:
    CDPDirectEngine = None  # type: ignore[misc,assignment]
    CDPDirectPage = None  # type: ignore[misc,assignment]
    CDPDirectStealthBridge = None  # type: ignore[misc,assignment]

__all__ = [
    "PatchrightEngine",
    "PatchrightPage",
    "PatchrightStealthBridge",
    "PlaywrightEngine",
    "PlaywrightPage",
    "PlaywrightStealthBridge",
    "SeleniumEngine",
    "SeleniumPage",
    "SeleniumStealthBridge",
    "CDPDirectEngine",
    "CDPDirectPage",
    "CDPDirectStealthBridge",
]
