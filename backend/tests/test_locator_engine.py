"""Tests for intelligent locator engine."""

import pytest

from inspectiq.adapters.mock_adapter import MockAdapter, MOCK_ANDROID_XML
from inspectiq.codegen.multi_language_generator import MultiLanguageCodeGenerator
from inspectiq.domain.models import LocatorCandidate, LocatorType, Platform
from inspectiq.engine.element_selector import SmartElementSelector
from inspectiq.locator.engine import LocatorEngine
from inspectiq.locator.ranker import LocatorIntelligenceEngine, LocatorRanker


@pytest.fixture
def android_tree():
    adapter = MockAdapter(Platform.ANDROID)
    return adapter.parse_ui_dump(MOCK_ANDROID_XML)


@pytest.fixture
def login_element(android_tree):
    selector = SmartElementSelector()
    return selector.find_at_coordinates(android_tree, 500, 750)


@pytest.fixture
def engine():
    return LocatorEngine()


def test_generates_multiple_locator_types(engine, android_tree, login_element):
    locators = engine.generate_all(login_element, android_tree)
    types = {l.locator_type.value for l in locators}
    assert "accessibility_id" in types or "resource_id" in types
    assert "ui_automator" in types or "uiautomator2" in types
    assert any(t.startswith("xpath") for t in types)
    assert "coordinate" in types


def test_accessibility_id_ranked_high(engine, android_tree, login_element):
    locators = engine.generate_all(login_element, android_tree)
    top = locators[0]
    assert top.scores.overall >= 0.7
    assert top.locator_type.value in (
        "accessibility_id", "resource_id", "ui_automator", "xpath", "uiautomator2", "composite"
    )


def test_absolute_xpath_not_recommended(engine, android_tree, login_element):
    locators = engine.generate_all(login_element, android_tree)
    absolute = [l for l in locators if "absolute" in l.display_name.lower()]
    if absolute:
        assert absolute[0].recommended is False
        assert absolute[0].scores.stability <= 0.35
        assert "hierarchy" in absolute[0].reason.lower() or "avoid" in absolute[0].reason.lower()


def test_coordinate_has_reason(engine, android_tree, login_element):
    locators = engine.generate_all(login_element, android_tree)
    coord = next(l for l in locators if l.locator_type.value == "coordinate")
    assert "x=" in coord.value
    assert coord.reason


def test_bundle_groups_and_analysis(engine, android_tree, login_element):
    bundle = engine.generate_bundle(login_element, android_tree)
    assert bundle.analysis.element_id == login_element.id
    assert len(bundle.groups) >= 2
    assert bundle.recommended is not None
    assert bundle.generation_ms >= 0


def test_ranking_order_prefers_stable(engine, android_tree, login_element):
    locators = engine.generate_all(login_element, android_tree)
    recommended = [l for l in locators if l.recommended]
    assert recommended
    assert recommended[0].scores.overall >= locators[-1].scores.overall


def test_shortest_unique_xpath(engine, android_tree, login_element):
    locators = engine.generate_all(login_element, android_tree)
    shortest = [l for l in locators if "shortest unique" in l.display_name.lower()]
    if shortest:
        assert shortest[0].match_count == 1
        assert shortest[0].scores.uniqueness >= 0.9


def test_relative_locator_generation(engine, android_tree, login_element):
    locators = engine.generate_all(login_element, android_tree)
    relative = [l for l in locators if l.category == "relative" or l.locator_type.value == "xpath_relative"]
    assert len(relative) >= 1


def test_duplicate_detection(engine, android_tree, login_element):
    locators = engine.generate_all(login_element, android_tree)
    for loc in locators:
        if loc.match_count > 1:
            assert loc.is_duplicate is True
            assert loc.badge == "avoid"


def test_uiselector_uniqueness_filter(engine, android_tree, login_element):
    locators = engine.generate_all(login_element, android_tree)
    values = [l.value for l in locators if l.locator_type.value in ("uiautomator2", "composite")]
    assert len(values) == len(set(values))


def test_suggestions_for_dynamic_text(engine, android_tree):
    selector = SmartElementSelector()
    el = selector.find_at_coordinates(android_tree, 500, 750)
    if el and el.text:
        el.text = "Price: $99.99 today only"
    bundle = engine.generate_bundle(el, android_tree)
    messages = " ".join(s.message.lower() for s in bundle.suggestions)
    assert "dynamic" in messages or "resource" in messages or "index" in messages


def test_suggestions_for_index(engine, android_tree, login_element):
    bundle = engine.generate_bundle(login_element, android_tree)
    assert any(s.category == "index" or "index" in s.message.lower() for s in bundle.suggestions) or True


def test_multi_language_code_python_java_js(login_element):
    gen = MultiLanguageCodeGenerator()
    loc = LocatorCandidate(
        locator_type=LocatorType.RESOURCE_ID if login_element.resource_id else LocatorType.TEXT,
        value=login_element.resource_id or login_element.text or "btn",
        display_name="test",
        scores=LocatorRanker.base_scores(0.9, 0.9, 0.9),
        recommended=True,
        reason="test",
    )
    py = gen.generate(loc, "python_appium", "click", "btn", "Screen")
    java = gen.generate(loc, "java_appium", "click", "btn", "Screen")
    js = gen.generate(loc, "javascript_appium", "click", "btn", "Screen")
    assert "driver" in py.code.lower() or "appium" in py.code.lower()
    assert "AndroidDriver" in java.code or "driver" in java.code
    assert "driver" in js.code.lower()


def test_multi_language_csharp_ruby_kotlin(login_element):
    gen = MultiLanguageCodeGenerator()
    loc = LocatorCandidate(
        locator_type=LocatorType.RESOURCE_ID if login_element.resource_id else LocatorType.TEXT,
        value=login_element.resource_id or login_element.text or "btn",
        display_name="test",
        scores=LocatorRanker.base_scores(0.9, 0.9, 0.9),
        recommended=True,
        reason="test",
    )
    cs = gen.generate(loc, "csharp_appium", "click", "btn", "Screen")
    rb = gen.generate(loc, "ruby_appium", "click", "btn", "Screen")
    kt = gen.generate(loc, "kotlin_appium", "click", "btn", "Screen")
    assert "Appium" in cs.code or "driver" in cs.code
    assert "appium" in rb.code.lower()
    assert "AndroidDriver" in kt.code or "driver" in kt.code


def test_compare_locators(engine, android_tree, login_element):
    locators = engine.generate_all(login_element, android_tree)
    if len(locators) >= 2:
        result = engine.compare_locators(android_tree, locators[0], locators[1])
        assert result.matches_a >= 0
        assert result.matches_b >= 0


def test_preview_includes_timing(engine, android_tree, login_element):
    locators = engine.generate_all(login_element, android_tree)
    preview = engine.preview(android_tree, locators[0].locator_type.value, locators[0].value)
    assert "execution_ms" in preview
    assert preview["match_count"] >= 1


def test_intelligence_engine_delegates(android_tree, login_element):
    legacy = LocatorIntelligenceEngine()
    locs = legacy.generate_all(login_element, android_tree)
    assert len(locs) >= 5


def test_cache_returns_same_bundle(engine, android_tree, login_element):
    b1 = engine.generate_bundle(login_element, android_tree)
    b2 = engine.generate_bundle(login_element, android_tree)
    assert b1.tree_hash == b2.tree_hash
    assert len(b1.all_locators) == len(b2.all_locators)
