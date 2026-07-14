"""Tests for screenshot ↔ hierarchy coordinate mapping."""

import pytest

from inspectiq.adapters.mock_adapter import MockAdapter, MOCK_ANDROID_XML
from inspectiq.domain.models import Bounds, Platform
from inspectiq.engine.coordinate_mapper import (
    build_coordinate_mapping,
    hierarchy_dimensions,
    hierarchy_to_screenshot_pct,
    screenshot_to_hierarchy,
)
from inspectiq.engine.element_selector import SmartElementSelector


@pytest.fixture
def android_tree():
    return MockAdapter(Platform.ANDROID).parse_ui_dump(MOCK_ANDROID_XML)


def test_hierarchy_dimensions_from_tree(android_tree):
    w, h = hierarchy_dimensions(android_tree)
    assert w == 1080
    assert h == 1920


def test_screenshot_to_hierarchy_identity():
    x, y = screenshot_to_hierarchy(540, 960, 1080, 1920, 1080, 1920)
    assert x == 540
    assert y == 960


def test_screenshot_to_hierarchy_independent_axes():
    # Screenshot larger than hierarchy on both axes (typical foldable / density mismatch)
    x, y = screenshot_to_hierarchy(612, 1496, 1080, 2400, 1224, 2992)
    assert x == 540
    assert y == 1200


def test_login_button_via_scaled_coordinates(android_tree):
    selector = SmartElementSelector()
    # Login button center in hierarchy space: ~(540, 750)
    # Same point on a 1224×2992 screenshot
    sx = int(540 * 1224 / 1080)
    sy = int(750 * 2992 / 1920)
    hx, hy = screenshot_to_hierarchy(sx, sy, 1080, 1920, 1224, 2992)
    element = selector.find_at_coordinates(android_tree, hx, hy)
    assert element is not None
    assert element.text == "Login"


def test_title_in_upper_half(android_tree):
    selector = SmartElementSelector()
    # "Welcome Back" bounds center ~ (540, 285) — upper half
    sx = int(540 * 1224 / 1080)
    sy = int(285 * 2992 / 1920)
    hx, hy = screenshot_to_hierarchy(sx, sy, 1080, 1920, 1224, 2992)
    element = selector.find_at_coordinates(android_tree, hx, hy)
    assert element is not None
    assert element.text == "Welcome Back"


def test_build_coordinate_mapping(android_tree):
    mapping = build_coordinate_mapping(android_tree, (1080, 1920), (1224, 2992), 0)
    assert mapping.hierarchy_width == 1080
    assert mapping.hierarchy_height == 1920
    assert mapping.screenshot_width == 1224
    assert mapping.screenshot_height == 2992
    assert abs(mapping.scale_x - 1080 / 1224) < 0.001
    assert abs(mapping.scale_y - 1920 / 2992) < 0.001

    pct = hierarchy_to_screenshot_pct(Bounds(x1=120, y1=700, x2=960, y2=800), 1080, 1920)
    assert pct["left"] == f"{120 / 1080 * 100}%"
    assert pct["top"] == f"{700 / 1920 * 100}%"
