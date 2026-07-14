"""Script assembly and per-step code generation."""

from __future__ import annotations

import re
from typing import List, Set

from inspectiq.codegen.multi_language_generator import MultiLanguageCodeGenerator
from inspectiq.domain.models import LocatorCandidate, LocatorScore, LocatorType
from inspectiq.recording.interfaces import CodeGenerationService
from inspectiq.recording.models import RecordedActionType, RecordedStep, RecordingSession, RecordingSettings

ACTION_MAP = {
    RecordedActionType.TAP: "click",
    RecordedActionType.DOUBLE_TAP: "double_click",
    RecordedActionType.LONG_PRESS: "long_click",
    RecordedActionType.SET_TEXT: "set_text",
    RecordedActionType.CLEAR_TEXT: "clear_text",
    RecordedActionType.SWIPE: "swipe",
    RecordedActionType.SCROLL: "scroll",
    RecordedActionType.PRESS_BACK: "press_back",
    RecordedActionType.PRESS_HOME: "press_home",
    RecordedActionType.PRESS_RECENT: "press_recent",
    RecordedActionType.OPEN_NOTIFICATION: "open_notification",
    RecordedActionType.WAIT: "wait",
    RecordedActionType.WAIT_VISIBLE: "wait_for_element",
    RecordedActionType.WAIT_CLICKABLE: "wait_for_element",
    RecordedActionType.WAIT_GONE: "wait_for_element",
    RecordedActionType.VERIFY_EXISTS: "assert_exists",
    RecordedActionType.VERIFY_VISIBLE: "is_displayed",
    RecordedActionType.VERIFY_ENABLED: "is_enabled",
    RecordedActionType.VERIFY_TEXT: "get_text",
    RecordedActionType.SCREENSHOT: "screenshot",
    RecordedActionType.LAUNCH_APP: "launch_app",
}

ACTION_COMMENT = {
    RecordedActionType.TAP: "Click",
    RecordedActionType.DOUBLE_TAP: "Double click",
    RecordedActionType.LONG_PRESS: "Long press",
    RecordedActionType.SET_TEXT: "Enter text",
    RecordedActionType.CLEAR_TEXT: "Clear text",
    RecordedActionType.SWIPE: "Swipe",
    RecordedActionType.SCROLL: "Scroll",
    RecordedActionType.PRESS_BACK: "Press back",
    RecordedActionType.PRESS_HOME: "Press home",
    RecordedActionType.VERIFY_EXISTS: "Verify element exists",
    RecordedActionType.VERIFY_VISIBLE: "Verify element visible",
    RecordedActionType.VERIFY_ENABLED: "Verify element enabled",
    RecordedActionType.VERIFY_TEXT: "Verify text",
    RecordedActionType.WAIT_VISIBLE: "Wait until visible",
    RecordedActionType.WAIT_CLICKABLE: "Wait until clickable",
}


class DefaultCodeGenerationService(CodeGenerationService):
    def __init__(self):
        self._gen = MultiLanguageCodeGenerator()

    def _element_name(self, step: RecordedStep) -> str:
        if step.element:
            raw = step.element.text or step.element.resource_id or step.element.content_desc or f"element_{step.step_number}"
            name = re.sub(r"[^a-zA-Z0-9_]", "_", str(raw).lower()).strip("_")
            return name[:40] or f"element_{step.step_number}"
        return f"element_{step.step_number}"

    def _element_label(self, step: RecordedStep) -> str:
        if not step.element:
            return "element"
        el = step.element
        if el.text:
            return el.text
        if el.content_desc:
            return el.content_desc
        if el.resource_id:
            return el.resource_id.split("/")[-1]
        return el.class_name.split(".")[-1] if el.class_name else "element"

    def _mask_text(self, text: str, settings: RecordingSettings) -> str:
        if settings.mask_passwords and len(text) >= 4:
            return "****"
        return text

    def _step_comment(self, step: RecordedStep, settings: RecordingSettings) -> str:
        if step.comment:
            return step.comment
        verb = ACTION_COMMENT.get(step.action_type, step.action_type.value.replace("_", " ").title())
        label = self._element_label(step)
        if step.action_type == RecordedActionType.SET_TEXT:
            return f"{verb} into {label}"
        return f"{verb} {label}"

    def _comment_prefix(self, settings: RecordingSettings) -> str:
        return "#" if settings.language_profile.startswith("python") else "//"

    def generate_step_code(self, step: RecordedStep, settings: RecordingSettings) -> str:
        if step.action_type == RecordedActionType.CUSTOM and step.code_snippet:
            return step.code_snippet

        action = ACTION_MAP.get(step.action_type, "click")
        text_val = self._mask_text(step.text_value or "your_text", settings)

        if not step.locator and step.action_type in (
            RecordedActionType.PRESS_BACK,
            RecordedActionType.PRESS_HOME,
            RecordedActionType.PRESS_RECENT,
            RecordedActionType.OPEN_NOTIFICATION,
        ):
            loc = LocatorCandidate(
                locator_type=LocatorType.COORDINATE,
                value="device",
                display_name="device",
                scores=LocatorScore(stability=1, uniqueness=1, maintainability=1, overall=1),
                recommended=True,
                reason="device action",
            )
        elif step.locator:
            loc = step.locator
        elif step.coordinates:
            loc = LocatorCandidate(
                locator_type=LocatorType.COORDINATE,
                value=f"{step.coordinates.get('x', 0)},{step.coordinates.get('y', 0)}",
                display_name="coordinate",
                scores=LocatorScore(stability=0.3, uniqueness=1, maintainability=0.2, overall=0.35),
                recommended=False,
                reason="coordinate fallback",
            )
        else:
            return f"# Step {step.step_number}: unresolved {step.action_type.value} — manual fix required"

        body = self._action_body(loc, action, step, settings, text_val)
        if settings.include_comments:
            prefix = self._comment_prefix(settings)
            return f"{prefix} {self._step_comment(step, settings)}\n{body}"
        return body

    def _action_body(
        self,
        loc: LocatorCandidate,
        action: str,
        step: RecordedStep,
        settings: RecordingSettings,
        text_val: str,
    ) -> str:
        profile = settings.language_profile

        if profile in ("python_uiautomator2", "adb_shell"):
            from inspectiq.codegen.uiautomator2_generator import UiAutomator2CodeGenerator

            u2 = UiAutomator2CodeGenerator()
            if profile == "adb_shell" or loc.locator_type == LocatorType.COORDINATE:
                script = self._gen.generate(
                    loc,
                    language_profile=profile,
                    action=action,
                    element_name=self._element_name(step),
                    page_name=settings.page_name,
                    text_value=text_val,
                    package_name=settings.package_name,
                )
                lines = [ln for ln in script.code.strip().split("\n") if ln.strip()]
                action_lines = [
                    ln for ln in lines
                    if ln.strip().startswith("d(") or ln.strip().startswith("d.")
                    or ln.strip().startswith("adb ")
                ]
                return "\n".join(action_lines) if action_lines else lines[-1]

            sel = u2._selector_expr(loc)
            if action == "click":
                return f"{sel}.click()"
            if action == "double_click":
                return f"{sel}.click()\n{sel}.click()"
            if action == "long_click":
                return f"{sel}.long_click()"
            if action == "set_text":
                return f'{sel}.set_text("{text_val}")'
            if action == "clear_text":
                return f"{sel}.clear_text()"
            if action == "press_back":
                return "d.press('back')"
            if action == "press_home":
                return "d.press('home')"
            if action == "press_recent":
                return "d.press('recent')"
            if action == "open_notification":
                return "d.open_notification()"
            if action == "scroll":
                return "d(scrollable=True).scroll.forward()"
            if action == "swipe":
                return "d.swipe(0.5, 0.8, 0.5, 0.2)"
            return f"{sel}.click()"

        if profile == "python_appium":
            by, val = self._gen._selector_appium_py(loc)
            if action == "click":
                return f"driver.find_element({by}, {repr(val)}).click()"
            if action == "double_click":
                return (
                    f"driver.find_element({by}, {repr(val)}).click()\n"
                    f"driver.find_element({by}, {repr(val)}).click()"
                )
            if action == "long_click":
                return (
                    f"driver.execute_script('mobile: longClickGesture', "
                    f"{{'elementId': driver.find_element({by}, {repr(val)}).id}})"
                )
            if action == "set_text":
                return (
                    f"el = driver.find_element({by}, {repr(val)})\n"
                    f"el.clear()\n"
                    f"el.send_keys({repr(text_val)})"
                )
            if action == "clear_text":
                return f"driver.find_element({by}, {repr(val)}).clear()"
            if action == "press_back":
                return "driver.back()"
            if action == "press_home":
                return "driver.press_keycode(3)"
            return f"driver.find_element({by}, {repr(val)}).click()"

        if profile.startswith("java"):
            sel = (
                self._gen._selector_java_appium(loc)
                if profile == "java_appium"
                else (self._gen._selector_java_uia(loc), "")
            )
            if profile == "java_appium":
                by, val = sel
                if action == "set_text":
                    return (
                        f'WebElement el = driver.findElement({by}("{val}"));\n'
                        f"el.clear();\n"
                        f'el.sendKeys("{text_val}");'
                    )
                return f'driver.findElement({by}("{val}")).click();'
            sel_expr = sel if isinstance(sel, str) else sel[0]
            return f"UiObject obj = device.findObject({sel_expr});\nobj.click();"

        if profile.startswith("javascript"):
            if profile == "javascript_appium":
                strategy, val = self._gen._selector_js_appium(loc)
                el = f"const el = await driver.findElement({{ using: '{strategy}', value: '{val}' }});"
            else:
                sel = self._gen._selector_js_wdio(loc)
                el = f"const el = await $('{sel}');"
            if action == "set_text":
                return f"{el}\nawait el.setValue('{text_val}');"
            if action == "clear_text":
                return f"{el}\nawait el.clearValue();"
            return f"{el}\nawait el.click();"

        # Fallback — uiautomator2-style one-liner
        script = self._gen.generate(
            loc,
            language_profile="python_uiautomator2",
            action=action,
            element_name=self._element_name(step),
            page_name=settings.page_name,
            text_value=text_val,
            package_name=settings.package_name,
        )
        return script.code.strip()

    def script_header(self, settings: RecordingSettings) -> str:
        profile = settings.language_profile
        if profile == "python_appium":
            return (
                '"""DroidLens Recording Studio — Appium Python."""\n'
                "from appium import webdriver\n"
                "from appium.webdriver.common.appiumby import AppiumBy\n"
                "from appium.options.android import UiAutomator2Options\n"
                "from selenium.webdriver.support.ui import WebDriverWait\n"
                "from selenium.webdriver.support import expected_conditions as EC\n\n"
                "options = UiAutomator2Options()\n"
                f'options.app_package = "{settings.package_name}"\n'
                "driver = webdriver.Remote('http://127.0.0.1:4723', options=options)\n"
                "wait = WebDriverWait(driver, 10)\n"
            )
        if profile.startswith("python"):
            return (
                '"""DroidLens Recording Studio — UIAutomator2 Python."""\n'
                "import uiautomator2 as u2\n\n"
                f'd = u2.connect()  # package: {settings.package_name}\n'
                f'd.app_start("{settings.package_name}")\n'
            )
        if profile == "java_appium":
            return (
                "// DroidLens Recording Studio — Appium Java\n"
                "import io.appium.java_client.android.AndroidDriver;\n"
                "import io.appium.java_client.AppiumBy;\n"
                "import org.openqa.selenium.support.ui.WebDriverWait;\n"
                "import org.openqa.selenium.support.ui.ExpectedConditions;\n"
                "import org.openqa.selenium.WebElement;\n\n"
                f"// AndroidDriver driver = new AndroidDriver(...); // package: {settings.package_name}\n"
                "// WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(10));\n"
            )
        if profile.startswith("java"):
            return (
                "// DroidLens Recording Studio — UIAutomator Java\n"
                "import androidx.test.uiautomator.UiDevice;\n"
                "import androidx.test.uiautomator.UiSelector;\n\n"
            )
        if profile == "javascript_appium":
            return (
                "// DroidLens Recording Studio — Appium JavaScript\n"
                "const { remote } = require('webdriverio');\n\n"
                "const driver = await remote({\n"
                "  hostname: '127.0.0.1',\n"
                "  port: 4723,\n"
                "  capabilities: { platformName: 'Android', 'appium:appPackage': "
                f'"{settings.package_name}" }},\n'
                "});\n"
            )
        if profile.startswith("javascript"):
            return "// DroidLens Recording Studio — WebdriverIO\nconst { remote } = require('webdriverio');\n\n"
        return "# DroidLens recorded script\n"

    def _footer(self, settings: RecordingSettings) -> str:
        if settings.language_profile.startswith("python"):
            return "\n# End of recorded script\n"
        return "\n// End of recorded script\n"

    def _helper_suggestions(self, session: RecordingSession) -> List[str]:
        """Suggest reusable helpers when similar locators repeat."""
        counts: dict[str, int] = {}
        for step in session.steps:
            if not step.enabled or not step.locator:
                continue
            key = f"{step.locator.locator_type}:{step.locator.value}:{step.action_type.value}"
            counts[key] = counts.get(key, 0) + 1
        suggestions: List[str] = []
        prefix = self._comment_prefix(session.settings)
        for key, count in counts.items():
            if count >= 3:
                match = next(
                    (
                        s for s in session.steps
                        if s.locator
                        and f"{s.locator.locator_type}:{s.locator.value}:{s.action_type.value}" == key
                    ),
                    None,
                )
                if not match:
                    continue
                name = self._element_name(match)
                suggestions.append(f"{prefix} Consider helper: def {name}_action(): ...  (used {count}x)")
        return suggestions

    def assemble_script(self, session: RecordingSession) -> str:
        settings = session.settings
        parts: List[str] = [self.script_header(settings)]
        seen_actions: Set[str] = set()
        for step in session.steps:
            if not step.enabled:
                continue
            snippet = step.code_snippet or self.generate_step_code(step, settings)
            if settings.automatic_waits and step.locator and step.action_type in (
                RecordedActionType.TAP,
                RecordedActionType.SET_TEXT,
                RecordedActionType.VERIFY_VISIBLE,
            ):
                wait_line = self._wait_line(step, settings)
                if wait_line and wait_line not in snippet:
                    parts.append(wait_line)
            if step.locator:
                dup_key = f"{step.action_type}:{step.locator.locator_type}:{step.locator.value}"
                if dup_key in seen_actions and step.action_type == RecordedActionType.TAP:
                    prefix = self._comment_prefix(settings)
                    parts.append(f"{prefix} Duplicate tap detected — review if needed")
                seen_actions.add(dup_key)
            parts.append(snippet)
            parts.append("")
        helpers = self._helper_suggestions(session)
        if helpers:
            parts.extend(helpers)
            parts.append("")
        parts.append(self._footer(settings))
        return "\n".join(parts).strip() + "\n"

    def append_step(self, session: RecordingSession, step: RecordedStep) -> str:
        settings = session.settings
        if not session.full_script.strip():
            session.full_script = self.script_header(settings)
        snippet = step.code_snippet or self.generate_step_code(step, settings)
        block = snippet
        if settings.automatic_waits and step.locator and step.action_type in (
            RecordedActionType.TAP,
            RecordedActionType.SET_TEXT,
        ):
            wait_line = self._wait_line(step, settings)
            if wait_line and wait_line not in snippet:
                block = f"{wait_line}\n{snippet}"
        footer = self._footer(settings).strip()
        base = session.full_script.rstrip()
        if base.endswith(footer):
            base = base[: -len(footer)].rstrip()
        session.full_script = f"{base}\n\n{block}\n{self._footer(settings)}"
        return session.full_script

    def _wait_line(self, step: RecordedStep, settings: RecordingSettings) -> str:
        if not step.locator:
            return ""
        loc = step.locator
        if loc.locator_type == LocatorType.COORDINATE:
            return ""

        profile = settings.language_profile
        timeout = settings.wait_timeout

        if profile == "python_appium":
            by, val = self._gen._selector_appium_py(loc)
            return f"wait.until(EC.presence_of_element_located(({by}, {repr(val)})))"

        if profile.startswith("python"):
            from inspectiq.codegen.uiautomator2_generator import UiAutomator2CodeGenerator

            sel = UiAutomator2CodeGenerator()._selector_expr(loc)
            if ".click(" in sel:
                return ""
            return f"{sel}.wait(timeout={timeout})"

        if profile == "java_appium":
            return f"// wait.until(ExpectedConditions.presenceOfElementLocated(...)); // timeout={timeout}s"
        if profile.startswith("javascript"):
            return f"// await driver.waitUntil(async () => ..., {{ timeout: {timeout * 1000} }});"
        return ""
