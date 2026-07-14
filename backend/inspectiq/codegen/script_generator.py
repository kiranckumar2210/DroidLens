"""Automation script generator for multiple languages."""

from __future__ import annotations

from inspectiq.domain.models import (
    GeneratedScript,
    LocatorCandidate,
    LocatorType,
    ScriptFramework,
    ScriptLanguage,
)


class ScriptGenerator:
    """Generates Appium automation scripts and Page Object Models."""

    def generate(
        self,
        locator: LocatorCandidate,
        language: ScriptLanguage = ScriptLanguage.PYTHON,
        framework: ScriptFramework = ScriptFramework.APPIUM,
        action: str = "click",
        page_name: str = "Page",
        element_name: str = "element",
    ) -> GeneratedScript:
        if language == ScriptLanguage.PYTHON:
            code = self._python(locator, action, page_name, element_name)
        elif language == ScriptLanguage.JAVA:
            code = self._java(locator, action)
        else:
            code = self._javascript(locator, action)

        return GeneratedScript(language=language, framework=framework, code=code, locator_used=locator)

    def _python(self, loc: LocatorCandidate, action: str, page_name: str, element_name: str) -> str:
        by, val = self._appium_by(loc)
        action_code = {
            "click": ".click()",
            "send_keys": '.send_keys("your_text")',
            "clear": ".clear()",
            "get_text": ".text",
        }.get(action, ".click()")

        inline = f'driver.find_element({by}, "{self._escape(val)}"){action_code}'

        pom = f'''class {page_name}:
    {element_name} = (
        {by},
        "{self._escape(val)}"
    )

    def {action}_{element_name}(self, driver):
        driver.find_element(*self.{element_name}){action_code}
'''

        return f"# Inline\n{inline}\n\n# Page Object Model\n{pom}"

    def _java(self, loc: LocatorCandidate, action: str) -> str:
        by, val = self._appium_by(loc)
        by_java = by.replace("AppiumBy.", "AppiumBy.")
        return f'driver.findElement({by_java}, "{self._escape(val)}").click();'

    def _javascript(self, loc: LocatorCandidate, action: str) -> str:
        mapping = {
            LocatorType.ACCESSIBILITY_ID: ("accessibility id",),
            LocatorType.RESOURCE_ID: ("id",),
            LocatorType.XPATH: ("xpath",),
            LocatorType.IOS_PREDICATE: ("-ios predicate string",),
            LocatorType.IOS_CLASS_CHAIN: ("-ios class chain",),
            LocatorType.UI_AUTOMATOR: ("-android uiautomator",),
            LocatorType.COORDINATE: ("touch",),
        }
        strategy, = mapping.get(loc.locator_type, ("xpath",))
        if loc.locator_type == LocatorType.COORDINATE:
            parts = dict(p.split("=") for p in loc.value.split(", "))
            return f"await driver.touchAction([{{ action: 'tap', x: {parts.get('x', 0)}, y: {parts.get('y', 0)} }}]);"
        return f'await driver.$("{strategy}:{loc.value}").click();'

    def _appium_by(self, loc: LocatorCandidate) -> tuple[str, str]:
        mapping = {
            LocatorType.ACCESSIBILITY_ID: "AppiumBy.ACCESSIBILITY_ID",
            LocatorType.RESOURCE_ID: "AppiumBy.ID",
            LocatorType.ID: "AppiumBy.ID",
            LocatorType.XPATH: "AppiumBy.XPATH",
            LocatorType.XPATH_CONTAINS: "AppiumBy.XPATH",
            LocatorType.XPATH_RELATIVE: "AppiumBy.XPATH",
            LocatorType.XPATH_AXIS: "AppiumBy.XPATH",
            LocatorType.UI_AUTOMATOR: "AppiumBy.ANDROID_UIAUTOMATOR",
            LocatorType.IOS_PREDICATE: "AppiumBy.IOS_PREDICATE",
            LocatorType.IOS_CLASS_CHAIN: "AppiumBy.IOS_CLASS_CHAIN",
            LocatorType.CONTENT_DESC: "AppiumBy.ACCESSIBILITY_ID",
        }
        by = mapping.get(loc.locator_type, "AppiumBy.XPATH")
        return by, loc.value

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')
