"""Tests for SessionConfig and SessionMode."""

from super_browser.browser import SessionConfig, SessionMode


class TestSessionMode:
    def test_all_modes(self):
        assert SessionMode.PATCHRIGHT_LAUNCH == "patchright_launch"
        assert SessionMode.PATCHRIGHT_ATTACH == "patchright_attach"
        assert SessionMode.DISCOVER == "discover"
        assert SessionMode.DAEMON == "daemon"


class TestSessionConfig:
    def test_defaults(self):
        cfg = SessionConfig()
        assert cfg.headless is False
        assert cfg.viewport == (1280, 720)
        assert cfg.default_timeout == 30.0
        assert cfg.stale_recovery is True
        assert cfg.event_buffer_size == 500
        assert cfg.mode == SessionMode.PATCHRIGHT_LAUNCH

    def test_frozen(self):
        cfg = SessionConfig()
        try:
            cfg.headless = True  # type: ignore
            assert False, "should raise"
        except AttributeError:
            pass

    def test_custom_values(self):
        cfg = SessionConfig(
            headless=True,
            viewport=(1920, 1080),
            proxy="http://proxy:8080",
            chrome_args=("--disable-gpu",),
        )
        assert cfg.headless is True
        assert cfg.viewport == (1920, 1080)
        assert cfg.proxy == "http://proxy:8080"
        assert cfg.chrome_args == ("--disable-gpu",)
