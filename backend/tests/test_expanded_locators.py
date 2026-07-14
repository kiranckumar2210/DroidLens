"""Tests for expanded locator generation."""

import pytest

from inspectiq.adapters.mock_adapter import MockAdapter, MOCK_ANDROID_XML
from inspectiq.domain.models import Platform
from inspectiq.engine.element_selector import SmartElementSelector
from inspectiq.locator.expanded_generators import ExpandedAndroidGenerator
from inspectiq.locator.locator_matcher import LocatorMatcher
from inspectiq.locator.ranker import LocatorIntelligenceEngine
from inspectiq.locator.relative_engine import RelativeLocatorEngine


@pytest.fixture
def android_tree():
    return MockAdapter(Platform.ANDROID).parse_ui_dump(MOCK_ANDROID_XML)


@pytest.fixture
def login_element(android_tree):
    return SmartElementSelector().find_at_coordinates(android_tree, 500, 750)


def test_expanded_resource_id_variants(login_element):
    gen = ExpandedAndroidGenerator()
    locs = gen.generate_all(login_element)
    names = {l.display_name for l in locs}
    assert "resourceId()" in names
    assert any("Contains" in n for n in names)
    assert any("StartsWith" in n for n in names)


def test_expanded_text_variants(login_element):
    gen = ExpandedAndroidGenerator()
    locs = [l for l in gen.generate_all(login_element) if "text" in l.display_name.lower()]
    assert len(locs) >= 3


def test_composite_locators(login_element):
    gen = ExpandedAndroidGenerator()
    locs = [l for l in gen.generate_all(login_element) if l.locator_type.value == "composite"]
    assert len(locs) >= 1


def test_relative_locators(login_element, android_tree):
    rel = RelativeLocatorEngine()
    locs = rel.generate_relative_locators(login_element, android_tree)
    assert len(locs) >= 1
    assert any(l.locator_type.value == "xpath_relative" for l in locs)


def test_engine_includes_expanded_and_relative(login_element, android_tree):
    engine = LocatorIntelligenceEngine()
    locs = engine.generate_all(login_element, android_tree)
    types = {l.locator_type.value for l in locs}
    assert "composite" in types or "uiautomator2" in types
    assert any(l.export_formats for l in locs)
    assert all(l.match_count >= 0 for l in locs)


def test_locator_matcher_u2_contains(android_tree, login_element):
    matcher = LocatorMatcher()
    rid = login_element.resource_id or ""
    short = rid.split("/")[-1]
    if short:
        count = matcher.count_matches(
            android_tree, "uiautomator2", f'd(resourceIdContains="{short[:6]}")'
        )
        assert count >= 1


def test_preview_endpoint_logic(login_element, android_tree):
    engine = LocatorIntelligenceEngine()
    locs = engine.generate_all(login_element, android_tree)
    top = locs[0]
    preview = engine.preview(android_tree, top.locator_type.value, top.value)
    assert preview["match_count"] >= 1
    assert preview["valid"] is True
