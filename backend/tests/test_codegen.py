"""Tests for multi-language code generation."""

import pytest

from inspectiq.codegen.multi_language_generator import MultiLanguageCodeGenerator
from inspectiq.domain.models import LocatorCandidate, LocatorScore, LocatorType


def _locator(ltype: LocatorType, value: str) -> LocatorCandidate:
    return LocatorCandidate(
        locator_type=ltype,
        value=value,
        display_name="Test",
        scores=LocatorScore(stability=0.9, uniqueness=0.9, maintainability=0.9, overall=0.9),
        recommended=True,
        reason="test",
    )


@pytest.fixture
def gen():
    return MultiLanguageCodeGenerator()


@pytest.mark.parametrize("profile", [
    "python_appium",
    "java_uiautomator",
    "java_appium",
    "javascript_wdio",
    "javascript_appium",
])
def test_profiles_generate_code(gen, profile):
    loc = _locator(LocatorType.RESOURCE_ID, "com.example:id/login")
    script = gen.generate(loc, profile, "click", "login_btn", "Login", "hello", "com.example.app")
    assert script.code
    assert "login" in script.code.lower() or "click" in script.code.lower()


@pytest.mark.parametrize("action", [
    "click", "long_click", "set_text", "wait", "get_text", "is_displayed", "launch_app",
])
def test_python_appium_actions(gen, action):
    loc = _locator(LocatorType.TEXT, "Login")
    script = gen.generate(loc, "python_appium", action, "login", "Login", "test", "com.app")
    assert script.code
    assert "appium" in script.code.lower() or "Appium" in script.code


def test_wait_for_element_normalized(gen):
    loc = _locator(LocatorType.TEXT, "Login")
    script = gen.generate(loc, "java_appium", "wait_for_element", "login", "Login")
    assert "wait" in script.code.lower() or "Wait" in script.code
