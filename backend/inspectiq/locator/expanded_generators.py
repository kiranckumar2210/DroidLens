"""Expanded Android locator variant generation."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from inspectiq.domain.models import ElementNode, LocatorCandidate, LocatorType
from inspectiq.locator.ranker import LocatorRanker


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _candidate(
    loc_type: LocatorType,
    value: str,
    display_name: str,
    stability: float,
    uniqueness: float,
    maintainability: float,
    reason: str,
    recommended: bool = False,
    exports: Optional[Dict[str, str]] = None,
) -> LocatorCandidate:
    return LocatorCandidate(
        locator_type=loc_type,
        value=value,
        display_name=display_name,
        scores=LocatorRanker.base_scores(stability, uniqueness, maintainability),
        recommended=recommended,
        reason=reason,
        framework_hint="uiautomator2",
        export_formats=exports or {},
    )


def _dynamic_id(rid: str) -> bool:
    if not rid:
        return False
    return bool(re.search(r"(/\d+|uuid|random|temp|0x[a-f0-9]+)", rid, re.I))


class ExpandedAndroidGenerator:
    """Generate comprehensive uiautomator2, UiSelector, and XPath variants."""

    def generate_all(self, element: ElementNode) -> List[LocatorCandidate]:
        results: List[LocatorCandidate] = []
        results.extend(self._resource_id_variants(element))
        results.extend(self._text_variants(element))
        results.extend(self._description_variants(element))
        results.extend(self._class_variants(element))
        results.extend(self._package_variants(element))
        results.extend(self._index_variants(element))
        results.extend(self._boolean_variants(element))
        results.extend(self._composite_variants(element))
        results.extend(self._ui_automator_variants(element))
        return results

    def _exports(self, u2: str, xpath: str = "", ui: str = "", appium: str = "") -> Dict[str, str]:
        d: Dict[str, str] = {"uiautomator2": u2}
        if xpath:
            d["xpath"] = xpath
        if ui:
            d["ui_automator"] = ui
        if appium:
            d["appium"] = appium
        return d

    def _resource_id_variants(self, el: ElementNode) -> List[LocatorCandidate]:
        if not el.resource_id:
            return []
        rid = el.resource_id
        short = rid.split("/")[-1] if "/" in rid else rid
        dynamic = _dynamic_id(rid)
        stab = 0.55 if dynamic else 0.93
        uniq = 0.60 if dynamic else 0.92
        reason_base = "Dynamic/generated resource ID — low stability" if dynamic else "Resource ID locator"

        variants: List[Tuple[str, str, float, float, str]] = [
            (f'd(resourceId="{_esc(rid)}")', "resourceId()", stab, uniq, reason_base),
            (f'd(resourceId="{_esc(short)}")', "resourceId (short)", stab - 0.05, uniq - 0.1, "Short resource-id suffix"),
            (f'd(resourceIdContains="{_esc(short[:12])}")', "resourceIdContains()", stab - 0.1, 0.75, "Partial resource-id match"),
            (f'd(resourceIdStartsWith="{_esc(short[:8])}")', "resourceIdStartsWith()", stab - 0.12, 0.72, "Resource-id prefix"),
            (f'd(resourceIdMatches=".*{_esc(short)}.*")', "resourceIdMatches() regex", stab - 0.15, 0.70, "Regex resource-id"),
        ]
        if len(short) > 4:
            variants.append((
                f'd(resourceIdEndsWith="{_esc(short[-6:])}")',
                "resourceIdEndsWith()", stab - 0.12, 0.68, "Resource-id suffix match",
            ))

        out = []
        for val, name, s, u, reason in variants:
            xpath = f"//*[@resource-id='{rid.replace(chr(39), '')}']"
            ui = f'new UiSelector().resourceId("{_esc(rid)}")'
            out.append(_candidate(
                LocatorType.UIAUTOMATOR2, val, name, s, u, 0.88, reason,
                recommended=not dynamic and name == "resourceId()",
                exports=self._exports(val, xpath, ui, f'id={short}'),
            ))
        return out

    def _text_variants(self, el: ElementNode) -> List[LocatorCandidate]:
        if not el.text:
            return []
        t = el.text
        volatile = len(t) > 40 or bool(re.search(r"\d{2,}|%|\$|€", t))
        stab = 0.55 if volatile else 0.78

        specs = [
            (f'd(text="{_esc(t)}")', "text()", stab, 0.70, "Exact text match"),
            (f'd(textContains="{_esc(t[:20])}")', "textContains()", stab - 0.05, 0.72, "Partial text — tolerates truncation"),
            (f'd(textStartsWith="{_esc(t[:10])}")', "textStartsWith()", stab - 0.08, 0.68, "Text prefix match"),
            (f'd(textMatches="(?i){_esc(t[:15])}")', "textMatches() case-insensitive", stab - 0.1, 0.65, "Case-insensitive regex text"),
        ]
        if len(t) > 3:
            specs.append((f'd(textEndsWith="{_esc(t[-5:])}")', "textEndsWith()", stab - 0.1, 0.62, "Text suffix match"))
            specs.append((f'd(textMatches=".*{_esc(t[:8])}.*")', "textMatches() regex", stab - 0.12, 0.60, "Regex text pattern"))

        out = []
        for val, name, s, u, reason in specs:
            xpath = f"//*[@text='{t.replace(chr(39), chr(92)+chr(39))}']"
            ui = f'new UiSelector().text("{_esc(t)}")'
            out.append(_candidate(
                LocatorType.TEXT if name == "text()" else LocatorType.UIAUTOMATOR2,
                val, name, s, u, 0.65, reason,
                exports=self._exports(val, xpath, ui, f'-android uiautomator:new UiSelector().text("{_esc(t)}")'),
            ))
        return out

    def _description_variants(self, el: ElementNode) -> List[LocatorCandidate]:
        desc = el.content_desc
        if not desc:
            return []
        specs = [
            (f'd(description="{_esc(desc)}")', "description()", 0.88, 0.85, "Exact content-desc"),
            (f'd(descriptionContains="{_esc(desc[:20])}")', "descriptionContains()", 0.82, 0.80, "Partial content-desc"),
            (f'd(descriptionStartsWith="{_esc(desc[:10])}")', "descriptionStartsWith()", 0.80, 0.78, "Content-desc prefix"),
            (f'd(descriptionMatches="(?i){_esc(desc[:12])}")', "descriptionMatches()", 0.78, 0.75, "Case-insensitive desc regex"),
        ]
        if len(desc) > 4:
            specs.append((f'd(descriptionEndsWith="{_esc(desc[-6:])}")', "descriptionEndsWith()", 0.76, 0.72, "Content-desc suffix"))

        out = []
        for val, name, s, u, reason in specs:
            out.append(_candidate(
                LocatorType.CONTENT_DESC if "Exact" in reason else LocatorType.UIAUTOMATOR2,
                val, name, s, u, 0.86, reason, recommended="Exact" in reason,
                exports=self._exports(val, f"//*[@content-desc='{desc}']", f'new UiSelector().description("{_esc(desc)}")'),
            ))
        return out

    def _class_variants(self, el: ElementNode) -> List[LocatorCandidate]:
        if not el.class_name:
            return []
        cn = el.class_name
        short = cn.split(".")[-1]
        specs = [
            (f'd(className="{_esc(cn)}")', "className()", 0.55, 0.45, "Full class name — rarely unique alone"),
            (f'd(classNameContains="{_esc(short)}")', "classNameContains()", 0.52, 0.50, "Short class name fragment"),
            (f'd(classNameMatches=".*{_esc(short)}")', "classNameMatches()", 0.50, 0.48, "Regex class match"),
        ]
        out = []
        for val, name, s, u, reason in specs:
            out.append(_candidate(LocatorType.CLASS_NAME, val, name, s, u, 0.45, reason, exports=self._exports(val)))
        return out

    def _package_variants(self, el: ElementNode) -> List[LocatorCandidate]:
        if not el.package:
            return []
        pkg = el.package
        return [
            _candidate(
                LocatorType.UIAUTOMATOR2, f'd(packageName="{_esc(pkg)}")', "packageName()",
                0.40, 0.30, 0.35, "Package scope — combine with other attributes",
                exports=self._exports(f'd(packageName="{_esc(pkg)}")'),
            ),
            _candidate(
                LocatorType.UIAUTOMATOR2, f'd(packageNameMatches=".*{_esc(pkg.split(".")[-1])}.*")',
                "packageNameMatches()", 0.38, 0.32, 0.33, "Regex package match",
                exports=self._exports(f'd(packageNameMatches=".*{_esc(pkg.split(".")[-1])}.*")'),
            ),
        ]

    def _index_variants(self, el: ElementNode) -> List[LocatorCandidate]:
        out = []
        if el.instance > 0 or el.index > 0:
            inst = el.instance if el.instance > 0 else el.index
            base = []
            if el.class_name:
                base.append(f'className="{_esc(el.class_name)}"')
            if el.resource_id:
                base.append(f'resourceId="{_esc(el.resource_id)}"')
            prefix = ", ".join(base)
            val = f"d({prefix}, instance={inst})" if prefix else f"d(instance={inst})"
            out.append(_candidate(
                LocatorType.INSTANCE, val, f"instance({inst})", 0.58, 0.82, 0.50,
                "Instance index — use when duplicates share class/id; fragile if order changes",
                exports=self._exports(val),
            ))
        if el.index >= 0:
            out.append(_candidate(
                LocatorType.UIAUTOMATOR2, f"d(index={el.index})", f"index({el.index})",
                0.50, 0.75, 0.42, "Sibling index — brittle, avoid as primary locator",
                exports=self._exports(f"d(index={el.index})"),
            ))
        return out

    def _boolean_variants(self, el: ElementNode) -> List[LocatorCandidate]:
        flags = [
            ("clickable", el.clickable), ("enabled", el.enabled), ("focused", el.focused),
            ("focusable", el.focusable), ("checkable", el.checkable), ("checked", el.checked),
            ("selected", el.selected), ("scrollable", el.scrollable),
            ("longClickable", el.long_clickable), ("password", el.password),
        ]
        active = [(k, v) for k, v in flags if v]
        if not active:
            return []

        parts = []
        if el.class_name:
            parts.append(f'className="{_esc(el.class_name)}"')
        for k, _ in active[:3]:
            parts.append(f"{k}=True")
        if el.text:
            parts.append(f'text="{_esc(el.text)}"')
        elif el.content_desc:
            parts.append(f'description="{_esc(el.content_desc)}"')

        if len(parts) < 2:
            return []

        val = f"d({', '.join(parts)})"
        return [_candidate(
            LocatorType.COMPOSITE, val, "Boolean attribute combo",
            0.65, 0.70, 0.60,
            f"Combines {', '.join(k for k, _ in active[:3])} with class/text for specificity",
            exports=self._exports(val),
        )]

    def _composite_variants(self, el: ElementNode) -> List[LocatorCandidate]:
        combos: List[LocatorCandidate] = []
        pairs: List[Tuple[str, str, str, float, str]] = []

        if el.resource_id and el.text:
            pairs.append((
                f'd(resourceId="{_esc(el.resource_id)}", text="{_esc(el.text)}")',
                "resource-id + text", 0.94, "Highly specific composite — resource ID anchors element, text confirms label",
            ))
        if el.resource_id and el.content_desc:
            pairs.append((
                f'd(resourceId="{_esc(el.resource_id)}", description="{_esc(el.content_desc)}")',
                "resource-id + description", 0.93, "Resource ID + content-desc composite",
            ))
        if el.text and el.class_name:
            short = el.class_name.split(".")[-1]
            pairs.append((
                f'd(text="{_esc(el.text)}", className="{_esc(el.class_name)}")',
                "text + class", 0.80, "Text with class disambiguation",
            ))
        if el.content_desc and el.class_name:
            pairs.append((
                f'd(description="{_esc(el.content_desc)}", className="{_esc(el.class_name)}")',
                "description + class", 0.85, "Content-desc with class filter",
            ))
        if el.resource_id and el.class_name:
            pairs.append((
                f'd(resourceId="{_esc(el.resource_id)}", className="{_esc(el.class_name)}")',
                "resource-id + class", 0.92, "Resource ID + class verification",
            ))
        if el.text and el.clickable:
            pairs.append((
                f'd(text="{_esc(el.text)}", clickable=True)',
                "text + clickable", 0.76, "Text on clickable element — good for buttons",
            ))
        if el.content_desc and el.enabled:
            pairs.append((
                f'd(description="{_esc(el.content_desc)}", enabled=True)',
                "description + enabled", 0.82, "Enabled element with accessibility desc",
            ))
        if el.class_name and el.package:
            pairs.append((
                f'd(className="{_esc(el.class_name)}", packageName="{_esc(el.package)}")',
                "class + package", 0.58, "Scoped to app package",
            ))
        if el.resource_id and el.package:
            pairs.append((
                f'd(resourceId="{_esc(el.resource_id)}", packageName="{_esc(el.package)}")',
                "resource-id + package", 0.90, "Resource ID within app package",
            ))

        for val, name, stab, reason in pairs:
            combos.append(_candidate(
                LocatorType.COMPOSITE, val, name, stab, 0.88, 0.85, reason,
                recommended=stab >= 0.90,
                exports=self._exports(val),
            ))
        return combos

    def _ui_automator_variants(self, el: ElementNode) -> List[LocatorCandidate]:
        """Java UiSelector equivalents for Appium Java users."""
        out = []
        if el.resource_id:
            ui = f'new UiSelector().resourceId("{_esc(el.resource_id)}")'
            out.append(_candidate(
                LocatorType.UI_AUTOMATOR, ui, "UiSelector resourceId",
                0.90, 0.92, 0.85, "Java UIAutomator resourceId",
                recommended=True, exports={"ui_automator": ui, "appium": ui},
            ))
        if el.text:
            ui = f'new UiSelector().text("{_esc(el.text)}")'
            out.append(_candidate(
                LocatorType.UI_AUTOMATOR, ui, "UiSelector text",
                0.75, 0.70, 0.72, "Java UIAutomator text",
                exports={"ui_automator": ui},
            ))
        if el.content_desc:
            ui = f'new UiSelector().description("{_esc(el.content_desc)}")'
            out.append(_candidate(
                LocatorType.UI_AUTOMATOR, ui, "UiSelector description",
                0.86, 0.84, 0.82, "Java UIAutomator description",
                exports={"ui_automator": ui},
            ))
        return out
