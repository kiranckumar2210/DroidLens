"""Multi-language automation code generator with Appium support."""

from __future__ import annotations

import re
from typing import Callable, Dict, List, Tuple

from inspectiq.codegen.uiautomator2_generator import UiAutomator2CodeGenerator
from inspectiq.domain.models import (
    GeneratedScript,
    LocatorCandidate,
    LocatorType,
    ScriptFramework,
    ScriptLanguage,
)


class MultiLanguageCodeGenerator:
    """Generate idiomatic automation code for Python, Java, and JavaScript."""

    PROFILES = {
        "python_uiautomator2": (ScriptLanguage.PYTHON, ScriptFramework.UIAUTOMATOR2),
        "python_appium": (ScriptLanguage.PYTHON, ScriptFramework.APPIUM),
        "java_uiautomator": (ScriptLanguage.JAVA, ScriptFramework.UIAUTOMATOR2),
        "java_appium": (ScriptLanguage.JAVA, ScriptFramework.APPIUM),
        "javascript_wdio": (ScriptLanguage.JAVASCRIPT, ScriptFramework.UIAUTOMATOR2),
        "javascript_appium": (ScriptLanguage.JAVASCRIPT, ScriptFramework.APPIUM),
        "csharp_appium": (ScriptLanguage.CSHARP, ScriptFramework.APPIUM),
        "ruby_appium": (ScriptLanguage.RUBY, ScriptFramework.APPIUM),
        "kotlin_appium": (ScriptLanguage.KOTLIN, ScriptFramework.APPIUM),
        "kotlin_uiautomator": (ScriptLanguage.KOTLIN, ScriptFramework.UIAUTOMATOR2),
        "adb_shell": (ScriptLanguage.PYTHON, ScriptFramework.ADB_SHELL),
    }

    ALL_ACTIONS = [
        "click", "long_click", "double_click", "set_text", "clear_text",
        "wait", "wait_for_element", "exists", "assert_exists",
        "scroll", "swipe", "drag", "screenshot",
        "press_back", "press_home", "open_notification",
        "launch_app", "close_app",
        "get_text", "get_attribute", "is_displayed", "is_enabled", "is_selected",
    ]

    def __init__(self):
        self._u2 = UiAutomator2CodeGenerator()

    def generate(
        self,
        locator: LocatorCandidate,
        language_profile: str = "python_uiautomator2",
        action: str = "click",
        element_name: str = "element",
        page_name: str = "Screen",
        text_value: str = "your_text",
        package_name: str = "com.example.app",
    ) -> GeneratedScript:
        profile = language_profile.lower()
        action = self._normalize_action(action)

        if profile == "python_uiautomator2":
            return self._u2.generate(locator, action, element_name, page_name, text_value)

        lang, framework = self.PROFILES.get(profile, (ScriptLanguage.JAVA, ScriptFramework.UIAUTOMATOR2))
        generators: Dict[str, Callable] = {
            "python_appium": self._python_appium,
            "java_uiautomator": self._java_uiautomator,
            "java_appium": self._java_appium,
            "javascript_wdio": self._javascript_wdio,
            "javascript_appium": self._javascript_appium,
            "csharp_appium": self._csharp_appium,
            "ruby_appium": self._ruby_appium,
            "kotlin_appium": self._kotlin_appium,
            "kotlin_uiautomator": self._kotlin_uiautomator,
            "adb_shell": self._adb_shell,
        }
        gen = generators.get(profile, self._java_uiautomator)
        code, pom = gen(locator, action, element_name, text_value, package_name, page_name)
        return GeneratedScript(
            language=lang,
            framework=framework,
            code=code,
            locator_used=locator,
            page_object=pom,
        )

    @staticmethod
    def _normalize_action(action: str) -> str:
        if action == "wait_for_element":
            return "wait"
        if action in ("check_displayed", "assert_displayed"):
            return "is_displayed"
        if action in ("check_enabled", "assert_enabled"):
            return "is_enabled"
        if action in ("check_selected", "assert_selected"):
            return "is_selected"
        return action

    # ------------------------------------------------------------------ selectors

    def _selector_u2(self, loc: LocatorCandidate) -> str:
        return self._u2._selector_expr(loc)

    def _selector_appium_py(self, loc: LocatorCandidate) -> Tuple[str, str]:
        if loc.locator_type in (LocatorType.RESOURCE_ID, LocatorType.ID):
            return "AppiumBy.ID", loc.value.split("/")[-1] if "/" in loc.value else loc.value
        if loc.locator_type == LocatorType.TEXT:
            return "AppiumBy.ANDROID_UIAUTOMATOR", f'new UiSelector().text("{loc.value}")'
        if loc.locator_type in (LocatorType.CONTENT_DESC, LocatorType.ACCESSIBILITY_ID):
            return "AppiumBy.ACCESSIBILITY_ID", loc.value
        if loc.locator_type == LocatorType.XPATH:
            return "AppiumBy.XPATH", loc.value
        if loc.locator_type == LocatorType.UI_AUTOMATOR:
            return "AppiumBy.ANDROID_UIAUTOMATOR", loc.value
        if loc.locator_type == LocatorType.CLASS_NAME:
            return "AppiumBy.CLASS_NAME", loc.value
        return "AppiumBy.XPATH", loc.value

    def _selector_java_uia(self, loc: LocatorCandidate) -> str:
        if loc.locator_type in (LocatorType.RESOURCE_ID, LocatorType.ID):
            return f'new UiSelector().resourceId("{loc.value}")'
        if loc.locator_type == LocatorType.TEXT:
            return f'new UiSelector().text("{loc.value}")'
        if loc.locator_type in (LocatorType.CONTENT_DESC, LocatorType.ACCESSIBILITY_ID):
            return f'new UiSelector().description("{loc.value}")'
        if loc.locator_type == LocatorType.UI_AUTOMATOR:
            inner = loc.value.replace("new UiSelector()", "").strip()
            return f"new UiSelector(){inner}"
        if loc.locator_type == LocatorType.XPATH:
            return f'By.xpath("{loc.value}")'
        return f'new UiSelector().className("{loc.value}")'

    def _selector_java_appium(self, loc: LocatorCandidate) -> Tuple[str, str]:
        if loc.locator_type in (LocatorType.RESOURCE_ID, LocatorType.ID):
            val = loc.value.split("/")[-1] if "/" in loc.value else loc.value
            return "AppiumBy.id", val
        if loc.locator_type == LocatorType.TEXT:
            return "AppiumBy.androidUIAutomator", f'new UiSelector().text("{loc.value}")'
        if loc.locator_type in (LocatorType.CONTENT_DESC, LocatorType.ACCESSIBILITY_ID):
            return "AppiumBy.accessibilityId", loc.value
        if loc.locator_type == LocatorType.XPATH:
            return "AppiumBy.xpath", loc.value
        if loc.locator_type == LocatorType.UI_AUTOMATOR:
            return "AppiumBy.androidUIAutomator", loc.value
        return "AppiumBy.xpath", loc.value

    def _selector_js_wdio(self, loc: LocatorCandidate) -> str:
        if loc.locator_type in (LocatorType.RESOURCE_ID, LocatorType.ID):
            return f'android=new UiSelector().resourceId("{loc.value}")'
        if loc.locator_type == LocatorType.TEXT:
            return f'android=new UiSelector().text("{loc.value}")'
        if loc.locator_type == LocatorType.XPATH:
            return loc.value
        if loc.locator_type == LocatorType.UI_AUTOMATOR:
            return loc.value.replace("new UiSelector()", "android=new UiSelector()")
        return f'~{loc.value}'

    def _selector_js_appium(self, loc: LocatorCandidate) -> Tuple[str, str]:
        if loc.locator_type in (LocatorType.RESOURCE_ID, LocatorType.ID):
            val = loc.value.split("/")[-1] if "/" in loc.value else loc.value
            return "id", val
        if loc.locator_type == LocatorType.TEXT:
            return "-android uiautomator", f'new UiSelector().text("{loc.value}")'
        if loc.locator_type in (LocatorType.CONTENT_DESC, LocatorType.ACCESSIBILITY_ID):
            return "accessibility id", loc.value
        if loc.locator_type == LocatorType.XPATH:
            return "xpath", loc.value
        if loc.locator_type == LocatorType.UI_AUTOMATOR:
            return "-android uiautomator", loc.value
        return "xpath", loc.value

    # ------------------------------------------------------------------ Python Appium

    def _python_appium(
        self, loc, action, element_name, text_value, package_name, page_name
    ) -> Tuple[str, str]:
        by, val = self._selector_appium_py(loc)
        el = f"element = driver.find_element({by}, {repr(val)})"
        wait_el = f"element = WebDriverWait(driver, 10).until(EC.presence_of_element_located(({by}, {repr(val)})))"

        actions = self._actions_appium_py(element_name, text_value, package_name, by, val, wait_el)
        body = actions.get(action, actions["click"])

        code = f'''"""Generated Appium Python script — {page_name}.{element_name}"""
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from appium.options.android import UiAutomator2Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configure capabilities for your device/emulator
options = UiAutomator2Options()
options.platform_name = "Android"
options.automation_name = "UiAutomator2"
options.app_package = "{package_name}"
options.app_activity = ".MainActivity"
options.no_reset = True

driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

try:
    # Locate element: {loc.display_name}
    {body}
except (TimeoutException, NoSuchElementException) as exc:
    raise AssertionError(f"Automation failed for {element_name}: {{exc}}") from exc
finally:
    driver.quit()
'''
        pom = f'''class {self._to_class(page_name)}:
    """Page Object — Appium Python."""

    def __init__(self, driver):
        self.driver = driver

    @property
    def {self._to_snake(element_name)}(self):
        return self.driver.find_element({by}, {repr(val)})
'''
        return code, pom

    def _actions_appium_py(self, name, text, pkg, by, val, wait_el) -> Dict[str, str]:
        return {
            "click": f"{wait_el}\n    element.click()  # Click {name}",
            "long_click": f"{wait_el}\n    driver.execute_script(\"mobile: longClickGesture\", {{\"elementId\": element.id}})",
            "double_click": f"{wait_el}\n    element.click()\n    element.click()  # Double click",
            "set_text": f"{wait_el}\n    element.clear()\n    element.send_keys(\"{text}\")  # Send text",
            "clear_text": f"{wait_el}\n    element.clear()  # Clear text field",
            "wait": f"{wait_el}\n    # Element is present and ready",
            "exists": f"found = len(driver.find_elements({by}, {repr(val)})) > 0",
            "assert_exists": f"{wait_el}\n    assert element.is_displayed(), \"Element not displayed\"",
            "scroll": f"{wait_el}\n    driver.execute_script(\"mobile: scrollGesture\", {{\"direction\": \"down\", \"percent\": 0.75}})",
            "swipe": "driver.execute_script(\"mobile: swipeGesture\", {\"direction\": \"up\", \"percent\": 0.75})",
            "drag": f"{wait_el}\n    driver.execute_script(\"mobile: dragGesture\", {{\"elementId\": element.id, \"endX\": 500, \"endY\": 500}})",
            "screenshot": "driver.save_screenshot(\"screen.png\")  # Full screen screenshot",
            "press_back": "driver.back()  # Press Back",
            "press_home": "driver.press_keycode(3)  # Press Home",
            "open_notification": "driver.open_notifications()  # Open notification shade",
            "launch_app": f"driver.activate_app(\"{pkg}\")  # Launch application",
            "close_app": f"driver.terminate_app(\"{pkg}\")  # Close application",
            "get_text": f"{wait_el}\n    text = element.text  # Get visible text",
            "get_attribute": f"{wait_el}\n    value = element.get_attribute(\"content-desc\")  # Get attribute",
            "is_displayed": f"{wait_el}\n    visible = element.is_displayed()  # Check displayed",
            "is_enabled": f"{wait_el}\n    enabled = element.is_enabled()  # Check enabled",
            "is_selected": f"{wait_el}\n    selected = element.is_selected()  # Check selected",
        }

    # ------------------------------------------------------------------ Java UIAutomator

    def _java_uiautomator(
        self, loc, action, element_name, text_value, package_name, page_name
    ) -> Tuple[str, str]:
        sel = self._selector_java_uia(loc)
        device = "UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())"
        if "UiSelector" in sel:
            el = f"UiObject {element_name} = {device}.findObject({sel});"
        else:
            el = f"UiObject2 {element_name} = {device}.findObject({sel});"

        actions = {
            "click": f"{el}\n        {element_name}.click();",
            "long_click": f"{el}\n        {element_name}.longClick();",
            "double_click": f"{el}\n        {element_name}.click();\n        {element_name}.click();",
            "set_text": f'{el}\n        {element_name}.setText("{text_value}");',
            "clear_text": f"{el}\n        {element_name}.clearTextField();",
            "wait": f"{el}\n        assertTrue(\"Element not found\", {element_name}.waitForExists(10000));",
            "exists": f"{el}\n        boolean found = {element_name}.exists();",
            "assert_exists": f"{el}\n        assertTrue({element_name}.exists());",
            "scroll": f"{device}.scrollForward();",
            "swipe": f"{device}.swipe(500, 1500, 500, 500, 10);",
            "drag": f"{el}\n        {element_name}.dragTo({device}.getDisplayWidth() / 2, {device}.getDisplayHeight() / 2, 50);",
            "screenshot": f"{device}.takeScreenshot(new File(\"screen.png\"));",
            "press_back": f"{device}.pressBack();",
            "press_home": f"{device}.pressHome();",
            "open_notification": f"{device}.openNotification();",
            "launch_app": f'{device}.executeShellCommand("monkey -p {package_name} -c android.intent.category.LAUNCHER 1");',
            "close_app": f'{device}.executeShellCommand("am force-stop {package_name}");',
            "get_text": f"{el}\n        String text = {element_name}.getText();",
            "get_attribute": f"{el}\n        String desc = {element_name}.getContentDescription();",
            "is_displayed": f"{el}\n        assertTrue({element_name}.exists());",
            "is_enabled": f"{el}\n        assertTrue({element_name}.isEnabled());",
            "is_selected": f"{el}\n        assertTrue({element_name}.isChecked());",
        }
        body = actions.get(action, actions["click"])
        code = f'''// Generated UIAutomator Java — {page_name}
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.uiautomator.*;
import org.junit.Assert.*;

public class {self._to_class(page_name)}Test {{
    public void {self._to_snake(element_name)}_{action}() throws Exception {{
        // Action: {action} on {element_name}
        {body}
    }}
}}
'''
        pom = f"// Page Object\nUiObject {element_name} = {device}.findObject({sel});"
        return code, pom

    # ------------------------------------------------------------------ Java Appium

    def _java_appium(
        self, loc, action, element_name, text_value, package_name, page_name
    ) -> Tuple[str, str]:
        by, val = self._selector_java_appium(loc)
        el = f"WebElement {element_name} = wait.until(ExpectedConditions.presenceOfElementLocated({by}(\"{val}\")));"

        actions = {
            "click": f"{el}\n            {element_name}.click();",
            "long_click": f"{el}\n            new TouchAction(driver).longPress(PointOption.point({element_name}.getLocation())).perform();",
            "double_click": f"{el}\n            {element_name}.click();\n            {element_name}.click();",
            "set_text": f'{el}\n            {element_name}.clear();\n            {element_name}.sendKeys("{text_value}");',
            "clear_text": f"{el}\n            {element_name}.clear();",
            "wait": el,
            "exists": f"boolean found = !driver.findElements({by}(\"{val}\")).isEmpty();",
            "assert_exists": f"{el}\n            assert {element_name}.isDisplayed();",
            "scroll": "driver.findElement(AppiumBy.androidUIAutomator(\"new UiScrollable(new UiSelector().scrollable(true)).scrollForward()\"));",
            "swipe": "driver.executeScript(\"mobile: swipeGesture\", Map.of(\"direction\", \"up\", \"percent\", 0.75));",
            "drag": f"{el}\n            driver.executeScript(\"mobile: dragGesture\", Map.of(\"elementId\", ((RemoteWebElement){element_name}).getId()));",
            "screenshot": "File screenshot = ((TakesScreenshot) driver).getScreenshotAs(OutputType.FILE);",
            "press_back": "driver.navigate().back();",
            "press_home": "driver.executeScript(\"mobile: pressKey\", Map.of(\"keycode\", 3));",
            "open_notification": "driver.openNotifications();",
            "launch_app": f"driver.executeScript(\"mobile: activateApp\", Map.of(\"appId\", \"{package_name}\"));",
            "close_app": f"driver.executeScript(\"mobile: terminateApp\", Map.of(\"appId\", \"{package_name}\"));",
            "get_text": f"{el}\n            String text = {element_name}.getText();",
            "get_attribute": f"{el}\n            String attr = {element_name}.getAttribute(\"content-desc\");",
            "is_displayed": f"{el}\n            boolean visible = {element_name}.isDisplayed();",
            "is_enabled": f"{el}\n            boolean enabled = {element_name}.isEnabled();",
            "is_selected": f"{el}\n            boolean selected = {element_name}.isSelected();",
        }
        body = actions.get(action, actions["click"])
        code = f'''// Generated Appium Java — {page_name}
import io.appium.java_client.*;
import io.appium.java_client.android.AndroidDriver;
import io.appium.java_client.AppiumBy;
import org.openqa.selenium.*;
import org.openqa.selenium.support.ui.*;
import java.net.URL;
import java.time.Duration;
import java.util.Map;

public class {self._to_class(page_name)}Test {{
    public static void main(String[] args) throws Exception {{
        DesiredCapabilities caps = new DesiredCapabilities();
        caps.setCapability("platformName", "Android");
        caps.setCapability("appium:automationName", "UiAutomator2");
        caps.setCapability("appium:appPackage", "{package_name}");
        caps.setCapability("appium:appActivity", ".MainActivity");

        AndroidDriver driver = new AndroidDriver(new URL("http://127.0.0.1:4723/"), caps);
        WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(10));

        try {{
            // {action} — {element_name}
            {body}
        }} catch (NoSuchElementException | TimeoutException e) {{
            throw new AssertionError("Element action failed: " + e.getMessage(), e);
        }} finally {{
            driver.quit();
        }}
    }}
}}
'''
        pom = f"// getter: WebElement get{self._to_class(element_name)}() {{ return driver.findElement({by}(\"{val}\")); }}"
        return code, pom

    # ------------------------------------------------------------------ JavaScript WDIO

    def _javascript_wdio(
        self, loc, action, element_name, text_value, package_name, page_name
    ) -> Tuple[str, str]:
        sel = self._selector_js_wdio(loc)
        el = f"const {element_name} = await $('{sel}');"

        actions = {
            "click": f"await {element_name}.click();",
            "long_click": f"await {element_name}.touchAction([{{ action: 'longPress', x: 0, y: 0 }}]);",
            "double_click": f"await {element_name}.doubleClick();",
            "set_text": f'await {element_name}.setValue("{text_value}");',
            "clear_text": f"await {element_name}.clearValue();",
            "wait": f"await {element_name}.waitForDisplayed({{ timeout: 10000 }});",
            "exists": f"const exists = await {element_name}.isDisplayed();",
            "assert_exists": f"await expect({element_name}).toBeDisplayed();",
            "scroll": f"await {element_name}.scrollIntoView();",
            "swipe": "await driver.touchAction([{ action: 'press', x: 500, y: 1500 }, { action: 'wait', ms: 200 }, { action: 'moveTo', x: 500, y: 500 }, { action: 'release' }]);",
            "drag": f"await {element_name}.dragAndDrop({{ x: 100, y: 100 }});",
            "screenshot": "await driver.saveScreenshot('./screen.png');",
            "press_back": "await driver.back();",
            "press_home": "await driver.pressKeyCode(3);",
            "open_notification": "await driver.openNotifications();",
            "launch_app": f"await driver.activateApp('{package_name}');",
            "close_app": f"await driver.terminateApp('{package_name}');",
            "get_text": f"const text = await {element_name}.getText();",
            "get_attribute": f"const attr = await {element_name}.getAttribute('content-desc');",
            "is_displayed": f"const visible = await {element_name}.isDisplayed();",
            "is_enabled": f"const enabled = await {element_name}.isEnabled();",
            "is_selected": f"const selected = await {element_name}.isSelected();",
        }
        line = actions.get(action, actions["click"])
        code = f'''// Generated WebdriverIO + Appium — {page_name}
// npm install @wdio/cli @wdio/appium-service appium

describe('{page_name}', () => {{
  it('should {action} {element_name}', async () => {{
    {el}
    {line}
  }});
}});
'''
        return code, f"get {element_name}() {{ return $('{sel}'); }}"

    # ------------------------------------------------------------------ JavaScript Appium

    def _javascript_appium(
        self, loc, action, element_name, text_value, package_name, page_name
    ) -> Tuple[str, str]:
        strategy, val = self._selector_js_appium(loc)
        el = f"const {element_name} = await driver.findElement({{ using: '{strategy}', value: '{val}' }});"

        actions = {
            "click": f"await {element_name}.click();",
            "long_click": f"await driver.execute('mobile: longClickGesture', {{ elementId: (await {element_name}.elementId) }});",
            "double_click": f"await {element_name}.click();\n    await {element_name}.click();",
            "set_text": f"await {element_name}.clear();\n    await {element_name}.sendKeys('{text_value}');",
            "clear_text": f"await {element_name}.clear();",
            "wait": f"await driver.waitUntil(async () => await {element_name}.isDisplayed(), {{ timeout: 10000 }});",
            "exists": f"const exists = await {element_name}.isDisplayed();",
            "assert_exists": f"if (!(await {element_name}.isDisplayed())) throw new Error('Element not found');",
            "scroll": "await driver.execute('mobile: scrollGesture', { direction: 'down', percent: 0.75 });",
            "swipe": "await driver.execute('mobile: swipeGesture', { direction: 'up', percent: 0.75 });",
            "drag": f"await driver.execute('mobile: dragGesture', {{ elementId: (await {element_name}.elementId) }});",
            "screenshot": "await driver.saveScreenshot('./screen.png');",
            "press_back": "await driver.back();",
            "press_home": "await driver.pressKeyCode(3);",
            "open_notification": "await driver.openNotifications();",
            "launch_app": f"await driver.execute('mobile: activateApp', {{ appId: '{package_name}' }});",
            "close_app": f"await driver.execute('mobile: terminateApp', {{ appId: '{package_name}' }});",
            "get_text": f"const text = await {element_name}.getText();",
            "get_attribute": f"const attr = await {element_name}.getAttribute('content-desc');",
            "is_displayed": f"const visible = await {element_name}.isDisplayed();",
            "is_enabled": f"const enabled = await {element_name}.isEnabled();",
            "is_selected": f"const selected = await {element_name}.isSelected();",
        }
        line = actions.get(action, actions["click"])
        code = f'''// Generated Appium JavaScript — {page_name}
const {{ remote }} = require('webdriverio');

(async () => {{
  const driver = await remote({{
    hostname: '127.0.0.1',
    port: 4723,
    path: '/',
    capabilities: {{
      platformName: 'Android',
      'appium:automationName': 'UiAutomator2',
      'appium:appPackage': '{package_name}',
      'appium:appActivity': '.MainActivity',
    }},
  }});

  try {{
    {el}
    {line}
  }} catch (err) {{
    console.error('Automation failed:', err);
    throw err;
  }} finally {{
    await driver.deleteSession();
  }}
}})();
'''
        return code, ""

    # ------------------------------------------------------------------ C# Appium

    def _csharp_appium(
        self, loc, action, element_name, text_value, package_name, page_name
    ) -> Tuple[str, str]:
        by, val = self._selector_csharp_appium(loc)
        el = f"var {element_name} = driver.FindElement({by}(\"{val}\"));"
        wait_el = f"var {element_name} = wait.Until(d => d.FindElement({by}(\"{val}\")));"
        actions = {
            "click": f"{wait_el}\n    {element_name}.Click();",
            "set_text": f'{wait_el}\n    {element_name}.Clear();\n    {element_name}.SendKeys("{text_value}");',
            "wait": wait_el,
            "exists": f"bool found = driver.FindElements({by}(\"{val}\")).Count > 0;",
        }
        body = actions.get(action, actions["click"])
        code = f'''// Generated Appium C# — {page_name}
using OpenQA.Selenium;
using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Appium.Android;
using OpenQA.Selenium.Support.UI;

var options = new AppiumOptions();
options.AddAdditionalAppiumOption("appium:automationName", "UiAutomator2");
options.AddAdditionalAppiumOption("appium:appPackage", "{package_name}");

using var driver = new AndroidDriver(new Uri("http://127.0.0.1:4723/"), options);
var wait = new WebDriverWait(driver, TimeSpan.FromSeconds(10));

try {{
    {body}
}} finally {{
    driver.Quit();
}}
'''
        return code, f"// IWebElement {element_name} => driver.FindElement({by}(\"{val}\"));"

    def _selector_csharp_appium(self, loc: LocatorCandidate) -> Tuple[str, str]:
        if loc.locator_type in (LocatorType.RESOURCE_ID, LocatorType.ID):
            val = loc.value.split("/")[-1] if "/" in loc.value else loc.value
            return "MobileBy.Id", val
        if loc.locator_type in (LocatorType.CONTENT_DESC, LocatorType.ACCESSIBILITY_ID):
            return "MobileBy.AccessibilityId", loc.value
        if loc.locator_type == LocatorType.XPATH:
            return "By.XPath", loc.value
        if loc.locator_type == LocatorType.UI_AUTOMATOR:
            return "MobileBy.AndroidUIAutomator", loc.value
        return "By.XPath", loc.value

    # ------------------------------------------------------------------ Ruby Appium

    def _ruby_appium(
        self, loc, action, element_name, text_value, package_name, page_name
    ) -> Tuple[str, str]:
        strategy, val = self._selector_ruby_appium(loc)
        el = f"{element_name} = @driver.find_element({strategy}: '{val}')"
        actions = {
            "click": f"{el}\n{element_name}.click",
            "set_text": f"{el}\n{element_name}.clear\n{element_name}.send_keys('{text_value}')",
            "wait": el,
            "exists": f"found = !@driver.find_elements({strategy}: '{val}').empty?",
        }
        body = actions.get(action, actions["click"])
        code = f'''# Generated Appium Ruby — {page_name}
require 'appium_lib'

caps = {{
  platformName: 'Android',
  'appium:automationName' => 'UiAutomator2',
  'appium:appPackage' => '{package_name}',
}}

@driver = Appium::Driver.new({{ caps: caps, appium_lib: {{ wait: 10 }} }}).start_driver

begin
  {body}
ensure
  @driver.driver_quit
end
'''
        return code, f"def {self._to_snake(element_name)}\n  @driver.find_element({strategy}: '{val}')\nend"

    def _selector_ruby_appium(self, loc: LocatorCandidate) -> Tuple[str, str]:
        if loc.locator_type in (LocatorType.RESOURCE_ID, LocatorType.ID):
            val = loc.value.split("/")[-1] if "/" in loc.value else loc.value
            return "id", val
        if loc.locator_type in (LocatorType.CONTENT_DESC, LocatorType.ACCESSIBILITY_ID):
            return "accessibility_id", loc.value
        if loc.locator_type == LocatorType.XPATH:
            return "xpath", loc.value
        if loc.locator_type == LocatorType.UI_AUTOMATOR:
            return "-android uiautomator", loc.value
        return "xpath", loc.value

    # ------------------------------------------------------------------ Kotlin Appium / UIAutomator

    def _kotlin_appium(
        self, loc, action, element_name, text_value, package_name, page_name
    ) -> Tuple[str, str]:
        sel = self._selector_kotlin_appium(loc)
        el = f"val {element_name} = driver.findElement({sel})"
        actions = {
            "click": f"{el}\n        {element_name}.click()",
            "set_text": f'{el}\n        {element_name}.clear()\n        {element_name}.sendKeys("{text_value}")',
            "wait": el,
            "exists": f"val found = driver.findElements({sel}).isNotEmpty()",
        }
        body = actions.get(action, actions["click"])
        code = f'''// Generated Appium Kotlin — {page_name}
import io.appium.java_client.android.AndroidDriver
import io.appium.java_client.AppiumBy
import java.net.URL
import java.time.Duration
import org.openqa.selenium.support.ui.WebDriverWait
import org.openqa.selenium.support.ui.ExpectedConditions

fun main() {{
    val caps = io.appium.java_client.remote.options.BaseOptions()
    caps.setCapability("platformName", "Android")
    caps.setCapability("appium:automationName", "UiAutomator2")
    caps.setCapability("appium:appPackage", "{package_name}")

    val driver = AndroidDriver(URL("http://127.0.0.1:4723/"), caps)
    val wait = WebDriverWait(driver, Duration.ofSeconds(10))

    try {{
        {body}
    }} finally {{
        driver.quit()
    }}
}}
'''
        return code, f"// val {element_name} get() = driver.findElement({sel})"

    def _kotlin_uiautomator(
        self, loc, action, element_name, text_value, package_name, page_name
    ) -> Tuple[str, str]:
        sel = self._selector_java_uia(loc)
        el = f"val {element_name} = device.findObject({sel})"
        actions = {
            "click": f"{el}\n        {element_name}.click()",
            "set_text": f'{el}\n        {element_name}.text = "{text_value}"',
            "wait": f"{el}\n        assert({element_name}.waitForExists(10_000))",
        }
        body = actions.get(action, actions["click"])
        code = f'''// Generated UIAutomator Kotlin — {page_name}
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.*

fun {self._to_snake(element_name)}_{action}() {{
    val device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
    {body}
}}
'''
        return code, el

    def _selector_kotlin_appium(self, loc: LocatorCandidate) -> str:
        if loc.locator_type in (LocatorType.RESOURCE_ID, LocatorType.ID):
            val = loc.value.split("/")[-1] if "/" in loc.value else loc.value
            return f'AppiumBy.id("{val}")'
        if loc.locator_type in (LocatorType.CONTENT_DESC, LocatorType.ACCESSIBILITY_ID):
            return f'AppiumBy.accessibilityId("{loc.value}")'
        if loc.locator_type == LocatorType.XPATH:
            return f'AppiumBy.xpath("{loc.value}")'
        if loc.locator_type == LocatorType.UI_AUTOMATOR:
            return f'AppiumBy.androidUIAutomator("{loc.value}")'
        return f'AppiumBy.xpath("{loc.value}")'

    # ------------------------------------------------------------------ ADB Shell

    def _adb_shell(
        self, loc, action, element_name, text_value, package_name, page_name
    ) -> Tuple[str, str]:
        coords = self._parse_coords(loc)
        x, y = coords if coords else (500, 500)
        actions = {
            "click": f"adb shell input tap {x} {y}",
            "long_click": f"adb shell input swipe {x} {y} {x} {y} 1000",
            "double_click": f"adb shell input tap {x} {y} && adb shell input tap {x} {y}",
            "set_text": f'adb shell input text "{text_value}"',
            "clear_text": "adb shell input keyevent 123 && adb shell input keyevent 67",
            "scroll": f"adb shell input swipe {x} {y + 200} {x} {y - 200} 300",
            "swipe": "adb shell input swipe 500 1500 500 500 300",
            "press_back": "adb shell input keyevent 4",
            "press_home": "adb shell input keyevent 3",
            "open_notification": "adb shell cmd statusbar expand-notifications",
            "launch_app": f"adb shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1",
            "close_app": f"adb shell am force-stop {package_name}",
            "screenshot": "adb exec-out screencap -p > screen.png",
            "wait": f"# Wait for element at ({x}, {y})",
            "exists": "# uiautomator dump && grep resource-id",
            "assert_exists": "# assert via uiautomator dump",
            "drag": f"adb shell input swipe {x} {y} {x + 100} {y + 100} 500",
            "get_text": "# adb shell uiautomator dump && parse XML",
            "get_attribute": "# parse node attributes from dump",
            "is_displayed": "# check bounds in UI dump",
            "is_enabled": "# check enabled attribute in dump",
            "is_selected": "# check selected attribute in dump",
        }
        line = actions.get(action, actions["click"])
        return f"# ADB Shell — {action}\n{line}", ""

    @staticmethod
    def _parse_coords(loc: LocatorCandidate):
        if loc.locator_type != LocatorType.COORDINATE:
            return None
        parts = dict(p.split("=") for p in loc.value.replace(",", "").split())
        try:
            return int(parts.get("x", 0)), int(parts.get("y", 0))
        except ValueError:
            return None

    @staticmethod
    def _to_class(name: str) -> str:
        parts = re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_").split("_")
        return "".join(p.capitalize() for p in parts if p) or "Screen"

    @staticmethod
    def _to_snake(name: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower()).strip("_")
        return s or "element"
