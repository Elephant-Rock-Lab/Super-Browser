"""Tests for coordinate utilities."""

from super_browser.vision.coords import normalize_coordinates, resize_coordinates, smart_resize


class TestResizeCoordinates:
    def test_exact_half(self):
        assert resize_coordinates(640, 360, (1280, 720), (1920, 1080)) == (960, 540)

    def test_identity(self):
        assert resize_coordinates(100, 200, (1280, 720), (1280, 720)) == (100, 200)

    def test_scaling(self):
        assert resize_coordinates(100, 50, (1280, 720), (1920, 1080)) == (150, 75)

    def test_zero(self):
        assert resize_coordinates(0, 0, (1280, 720), (1920, 1080)) == (0, 0)

    def test_max_coords(self):
        assert resize_coordinates(1280, 720, (1280, 720), (1920, 1080)) == (1920, 1080)

    def test_rounding(self):
        assert resize_coordinates(100, 100, (1000, 1000), (300, 300)) == (30, 30)


class TestNormalizeCoordinates:
    def test_absolute(self):
        nx, ny = normalize_coordinates(640, 360, "absolute", (1280, 720))
        assert nx == 0.5
        assert abs(ny - 0.5) < 0.01

    def test_relative(self):
        nx, ny = normalize_coordinates(500, 500, "relative", (1280, 720))
        assert nx == 0.5
        assert ny == 0.5

    def test_zero(self):
        nx, ny = normalize_coordinates(0, 0, "absolute", (1000, 1000))
        assert nx == 0.0
        assert ny == 0.0


class TestSmartResize:
    def test_within_bounds(self):
        w, h = smart_resize(1280, 720)
        assert w % 28 == 0
        assert h % 28 == 0

    def test_below_min(self):
        w, h = smart_resize(10, 10)
        assert w >= 28
        assert h >= 28
        assert w * h >= 3136

    def test_above_max(self):
        w, h = smart_resize(4000, 4000)
        assert w * h <= 784000 + 28 * 28

    def test_factor_alignment(self):
        w, h = smart_resize(100, 100)
        assert w % 28 == 0
        assert h % 28 == 0
