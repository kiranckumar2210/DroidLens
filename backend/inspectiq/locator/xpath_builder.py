"""Advanced XPath generation with axes support."""

from __future__ import annotations

from typing import Optional

from inspectiq.domain.models import ElementNode, Platform, XPathExample
from inspectiq.locator.relative_engine import RelativeLocatorEngine


class XPathBuilder:
    """Generates XPath locators with multiple strategies and axes."""

    def __init__(self) -> None:
        self._relative = RelativeLocatorEngine()

    def build_all(self, element: ElementNode, tree: Optional[ElementNode] = None) -> list[XPathExample]:
        examples: list[XPathExample] = []

        if element.text:
            examples.extend(self._text_xpaths(element.text))
        if element.resource_id:
            rid = element.resource_id
            short = rid.split("/")[-1]
            examples.append(XPathExample(
                axis="exact",
                xpath=f"//*[@resource-id='{self._escape(rid)}']",
                description="Exact resource-id match",
            ))
            examples.append(XPathExample(
                axis="contains",
                xpath=f"//*[contains(@resource-id,'{self._escape(short)}')]",
                description="Partial resource-id (contains)",
            ))
        if element.content_desc:
            desc = element.content_desc
            examples.extend([
                XPathExample(
                    axis="exact",
                    xpath=f"//*[@content-desc='{self._escape(desc)}']",
                    description="Exact content-desc match",
                ),
                XPathExample(
                    axis="contains",
                    xpath=f"//*[contains(@content-desc,'{self._escape(desc[:20])}')]",
                    description="Partial content-desc match",
                ),
            ])
            if len(desc) > 4:
                examples.append(XPathExample(
                    axis="ends-with",
                    xpath=(
                        f"//*[substring(@content-desc, string-length(@content-desc)"
                        f" - {len(desc[-6:])} + 1)='{self._escape(desc[-6:])}']"
                    ),
                    description="Content-desc ends-with match",
                ))

        if element.class_name:
            short_class = element.class_name.split(".")[-1]
            if element.text:
                examples.append(XPathExample(
                    axis="composite",
                    xpath=f"//{short_class}[@text='{self._escape(element.text)}']",
                    description="Class + text combination",
                ))
            if element.resource_id:
                examples.append(XPathExample(
                    axis="composite",
                    xpath=f"//{short_class}[@resource-id='{self._escape(element.resource_id)}']",
                    description="Class + resource-id combination",
                ))

        if tree:
            rel = self._relative.generate_relative_xpaths(element, tree)
            examples.extend(rel)

        text_for_axes = element.text or element.label or element.content_desc or ""
        if text_for_axes:
            escaped = self._escape(text_for_axes)
            for axis, suffix, desc in [
                ("parent", "/parent::*", "Navigate to parent element"),
                ("child", "/*", "Direct child elements"),
                ("first-child", "/*[1]", "First direct child"),
                ("last-child", "/*[last()]", "Last direct child"),
                ("ancestor", "/ancestor::*[1]", "Nearest ancestor"),
                ("descendant", "//*", "All descendant elements"),
                ("following", "/following::*[1]", "First following element"),
                ("following-sibling", "/following-sibling::*[1]", "Next sibling"),
                ("preceding", "/preceding::*[1]", "First preceding element"),
                ("preceding-sibling", "/preceding-sibling::*[1]", "Previous sibling"),
            ]:
                if element.platform == Platform.IOS:
                    xpath = f"//*[@label='{escaped}']{suffix}"
                else:
                    xpath = f"//*[@text='{escaped}']{suffix}"
                examples.append(XPathExample(axis=axis, xpath=xpath, description=desc))

        if element.index >= 0 and element.class_name:
            short = element.class_name.split(".")[-1]
            examples.append(XPathExample(
                axis="nth-child",
                xpath=f"//{short}[{element.index + 1}]",
                description=f"Nth matching {short} (position {element.index + 1})",
            ))

        return examples

    @staticmethod
    def _text_xpaths(text: str) -> list[XPathExample]:
        escaped = XPathBuilder._escape(text)
        items = [
            XPathExample(axis="exact", xpath=f"//*[@text='{escaped}']", description="Exact text match"),
            XPathExample(
                axis="contains",
                xpath=f"//*[contains(@text,'{XPathBuilder._escape(text[:20])}')]",
                description="Partial text match (contains)",
            ),
        ]
        if len(text) > 3:
            prefix = text[:3]
            items.append(XPathExample(
                axis="starts-with",
                xpath=f"//*[starts-with(@text,'{XPathBuilder._escape(prefix)}')]",
                description="Text starts-with match",
            ))
            suffix = text[-5:]
            items.append(XPathExample(
                axis="ends-with",
                xpath=(
                    f"//*[substring(@text, string-length(@text) - {len(suffix)} + 1)"
                    f"='{XPathBuilder._escape(suffix)}']"
                ),
                description="Text ends-with match",
            ))
        return items

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("'", "\\'").replace('"', '\\"')

    def build_relative(self, element: ElementNode) -> str:
        parts = []
        if element.class_name:
            short = element.class_name.split(".")[-1]
            parts.append(short)
        if element.text:
            parts.append(f"[@text='{self._escape(element.text)}']")
        elif element.resource_id:
            parts.append(f"[@resource-id='{self._escape(element.resource_id)}']")
        elif element.content_desc:
            parts.append(f"[@content-desc='{self._escape(element.content_desc)}']")
        return f"//{''.join(parts)}" if parts else "//*"
