import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires a real browser")


@pytest.fixture
def mock_page():
    """A mock page object with configurable evaluate() return value."""
    class MockPage:
        def __init__(self, return_value=1, raise_exc=None):
            self._return_value = return_value
            self._raise_exc = raise_exc

        def evaluate(self, expr):
            if self._raise_exc:
                raise self._raise_exc
            return self._return_value

    return MockPage
