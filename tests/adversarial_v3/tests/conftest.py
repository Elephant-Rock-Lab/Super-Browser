"""Pytest configuration and fixtures for adversarial3 test suite."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from adversarial3.backends import StubBackend
from adversarial3.core import BrowserBackend, EvaluationContext
from adversarial3.server import ControlledDetectionServer


def pytest_addoption(parser):
    parser.addoption("--tier1", action="store_true", default=False,
                     help="Run Tier 1 adversarial tests")
    parser.addoption("--tier2", action="store_true", default=False,
                     help="Run Tier 2 adversarial tests")
    parser.addoption("--tier3", action="store_true", default=False,
                     help="Run Tier 3 adversarial tests")
    parser.addoption("--all-tiers", action="store_true", default=False,
                     help="Run all adversarial tiers")
    parser.addoption("--backend", choices=["auto", "playwright", "stub"],
                     default="stub", help="Browser backend for tests")


def pytest_collection_modifyitems(config, items):
    tier1 = config.getoption("--tier1") or os.environ.get("SB_ADV", "0") == "1"
    tier2 = config.getoption("--tier2") or (
        os.environ.get("SB_ADV", "0") == "1"
        and os.environ.get("SB_ADV_VENDORS", "0") == "1"
        and os.environ.get("SB_ADV_VENDORS_ACK", "0") == "1"
    )
    tier3 = config.getoption("--tier3") or config.getoption("--all-tiers")
    all_t = config.getoption("--all-tiers")

    skip1 = pytest.mark.skip(reason="Tier 1 not enabled: use --tier1 or set SB_ADV=1")
    skip2 = pytest.mark.skip(reason="Tier 2 not enabled")
    skip3 = pytest.mark.skip(reason="Tier 3 not enabled: use --tier3 or --all-tiers")

    for item in items:
        if "tier1" in item.keywords and not (tier1 or all_t):
            item.add_marker(skip1)
        if "tier2" in item.keywords and not (tier2 or all_t):
            item.add_marker(skip2)
        if "tier3" in item.keywords and not (tier3 or all_t):
            item.add_marker(skip3)


@pytest.fixture(scope="session")
def report_dir():
    path = Path(os.environ.get("SB_ADV_REPORT_DIR", "adversarial-results"))
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(scope="session")
def backend_name(pytestconfig):
    return pytestconfig.getoption("--backend")


@pytest.fixture(scope="session")
def tier1_enabled(pytestconfig):
    return pytestconfig.getoption("--tier1") or os.environ.get("SB_ADV", "0") == "1"


@pytest.fixture(scope="session")
def tier2_enabled(pytestconfig):
    return pytestconfig.getoption("--tier2") or (
        os.environ.get("SB_ADV", "0") == "1"
        and os.environ.get("SB_ADV_VENDORS", "0") == "1"
        and os.environ.get("SB_ADV_VENDORS_ACK", "0") == "1"
    )


@pytest.fixture
async def browser(backend_name):
    from adversarial3.backends import create_backend
    backend = create_backend(backend_name)
    async with backend:
        yield backend


@pytest.fixture
def controlled_server():
    with ControlledDetectionServer() as server:
        yield server


@pytest.fixture
async def evaluation_context(browser, controlled_server):
    page = await browser.new_page()
    yield EvaluationContext(
        page=page, browser=browser, server_url=controlled_server.base_url, headers={}
    )
    await page.close()
