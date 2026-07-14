"""Python uiautomator2 code and Page Object generator."""

from __future__ import annotations

import re
from typing import List, Optional

from inspectiq.domain.models import (
    ElementNode,
    GeneratedScript,
    LocatorCandidate,
    LocatorType,
    ScriptFramework,
    ScriptLanguage,
)


class UiAutomator2CodeGenerator:
    """Generate production-ready uiautomator2 Python code."""

    ACTIONS = {
        "click": ("click", "Click element"),
        "long_click": ("long_click", "Long click element"),
        "double_click": ("click", "Double click (call twice)"),
        "set_text": ('set_text("{value}")', "Input text"),
        "clear_text": ("clear_text", "Clear text field"),
        "scroll": ("scroll.forward", "Scroll forward"),
        "swipe": ("swipe", "Swipe gesture"),
        "wait": ("wait(timeout=10)", "Wait until exists"),
        "exists": ("exists", "Check existence"),
        "assert_exists": ("wait(timeout=5)", "Assert element exists"),
        "screenshot": ("screenshot", "Screenshot element"),
        "drag": ("drag_to", "Drag element"),
        "pinch_in": ("pinch_in", "Pinch in"),
        "pinch_out": ("pinch_out", "Pinch out"),
        "press_back": ("press('back')", "Press back"),
        "press_home": ("press('home')", "Press home"),
        "press_recent": ("press('recent')", "Press recent apps"),
        "open_notification": ("open_notification", "Open notification shade"),
        "launch_app": ("app_start", "Launch application"),
        "close_app": ("app_stop", "Close application"),
        "get_text": ("get_text", "Get element text"),
        "get_attribute": ("info", "Get element info/attributes"),
        "is_displayed": ("exists", "Check if displayed"),
        "is_enabled": ("info", "Check if enabled"),
        "is_selected": ("info", "Check if selected"),
    }

    def generate(
        self,
        locator: LocatorCandidate,
        action: str = "click",
        element_name: str = "element",
        screen_name: str = "Screen",
        text_value: str = "your_text",
    ) -> GeneratedScript:
        method, _ = self.ACTIONS.get(action, ("click", ""))

        if action in ("press_back", "press_home", "press_recent"):
            line = f"d.{method}"
            return GeneratedScript(
                language=ScriptLanguage.PYTHON,
                framework=ScriptFramework.UIAUTOMATOR2,
                code=line,
                locator_used=locator,
            )
        if action == "open_notification":
            return GeneratedScript(
                language=ScriptLanguage.PYTHON,
                framework=ScriptFramework.UIAUTOMATOR2,
                code="d.open_notification()",
                locator_used=locator,
            )

        selector = self._selector_expr(locator)

        if action == "set_text":
            line = f'{selector}.{method.format(value=text_value)}'
        elif action in ("press_back", "press_home", "press_recent"):
            line = f"d.{method}"
        elif action == "wait":
            line = f"{selector}.wait(timeout=10)"
        elif action == "exists":
            line = f"assert {selector}.exists"
        elif action == "assert_exists":
            line = f"{selector}.wait(timeout=5)"
        elif action == "double_click":
            line = f"{selector}.click()\n{selector}.click()"
        elif action == "open_notification":
            line = "d.open_notification()"
        elif action == "launch_app":
            line = f'd.app_start("{text_value}")'
        elif action == "close_app":
            line = f'd.app_stop("{text_value}")'
        elif action == "get_text":
            line = f"text = {selector}.get_text()"
        elif action == "get_attribute":
            line = f"info = {selector}.info"
        elif action == "is_displayed":
            line = f"visible = {selector}.exists"
        elif action == "is_enabled":
            line = f"enabled = {selector}.info.get('enabled')"
        elif action == "is_selected":
            line = f"selected = {selector}.info.get('selected')"
        elif action in ("scroll", "swipe", "drag", "screenshot"):
            line = f"{selector}.{method}()" if "()" not in method else f"{selector}.{method}"
        else:
            line = f"{selector}.{method}()" if not method.startswith("press") else f"d.{method}"

        inline = f"import uiautomator2 as u2\n\nd = u2.connect()\n{line}"

        page_object = self.generate_page_object(
            screen_name, [(element_name, locator, action)]
        )

        return GeneratedScript(
            language=ScriptLanguage.PYTHON,
            framework=ScriptFramework.UIAUTOMATOR2,
            code=inline,
            locator_used=locator,
            page_object=page_object,
        )

    def generate_page_object(
        self,
        class_name: str,
        elements: List[tuple],
    ) -> str:
        safe_class = self._to_class_name(class_name)
        lines = [
            '"""Auto-generated Page Object for uiautomator2."""',
            "",
            "from __future__ import annotations",
            "",
            "import uiautomator2 as u2",
            "from uiautomator2 import Device",
            "",
            "",
            f"class {safe_class}:",
            '    """Screen object with lazy uiautomator2 selectors."""',
            "",
            "    def __init__(self, device: Device) -> None:",
            "        self.d = device",
            "",
        ]

        for name, locator, action in elements:
            selector = self._selector_expr(locator)
            prop = self._to_snake(name)
            lines.extend([
                "    @property",
                f"    def {prop}(self):",
                f'        """Locator: {locator.display_name}"""',
                f"        return {selector.replace('d.', 'self.d.')}",
                "",
            ])

        lines.extend([
            "    @classmethod",
            f"    def connect(cls, serial=None) -> \"{safe_class}\":",
            "        device = u2.connect(serial)",
            "        return cls(device)",
            "",
        ])

        return "\n".join(lines)

    def generate_wrapper_export(
        self,
        screen_name: str,
        elements: List[tuple[ElementNode, LocatorCandidate]],
    ) -> str:
        """Full production wrapper with methods per element."""
        safe_class = self._to_class_name(screen_name)
        lines = [
            '"""DroidLens generated screen wrapper — uiautomator2."""',
            "",
            "from __future__ import annotations",
            "",
            "import uiautomator2 as u2",
            "from uiautomator2 import Device",
            "",
            "",
            f"class {safe_class}:",
            "",
            "    def __init__(self, device: Device) -> None:",
            "        self.d = device",
            "",
        ]

        for element, locator in elements:
            name = self._to_snake(
                element.resource_id.split("/")[-1] if element.resource_id
                else element.text or element.content_desc or element.class_name.split(".")[-1]
            )
            selector = self._selector_expr(locator).replace("d.", "self.d.")
            lines.extend([
                f"    def {name}(self):",
                f'        """{element.display_type()}: {locator.value[:80]}"""',
                f"        return {selector}",
                "",
                f"    def tap_{name}(self) -> None:",
                f"        self.{name}().click()",
                "",
            ])

        return "\n".join(lines)

    def _selector_expr(self, locator: LocatorCandidate) -> str:
        if locator.locator_type == LocatorType.UIAUTOMATOR2:
            val = locator.value
            if val.startswith("d("):
                return val
            return f"d({val})"
        if locator.locator_type == LocatorType.RESOURCE_ID:
            return f'd(resourceId="{locator.value}")'
        if locator.locator_type == LocatorType.TEXT:
            return f'd(text="{locator.value}")'
        if locator.locator_type == LocatorType.CONTENT_DESC:
            return f'd(description="{locator.value}")'
        if locator.locator_type == LocatorType.CLASS_NAME:
            return f'd(className="{locator.value}")'
        if locator.locator_type == LocatorType.COORDINATE:
            parts = dict(p.split("=") for p in locator.value.replace(",", "").split())
            x = parts.get("x", "0")
            y = parts.get("y", "0")
            return f"d.click({x}, {y})  # coordinate"
        return f"d({locator.value})"

    @staticmethod
    def _to_class_name(name: str) -> str:
        parts = re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_").split("_")
        return "".join(p.capitalize() for p in parts if p) or "Screen"

    @staticmethod
    def _to_snake(name: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower()).strip("_")
        return s or "element"
