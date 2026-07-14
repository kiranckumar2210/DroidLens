"""Match locator expressions against element trees for validation and counting."""

from __future__ import annotations

import re
from typing import Callable, List, Optional

from inspectiq.domain.models import ElementNode


class LocatorMatcher:
    """Evaluate generated locators against a UI hierarchy (heuristic matching)."""

    def count_matches(self, tree: ElementNode, locator_type: str, value: str) -> int:
        predicate = self.build_predicate(locator_type, value)
        if predicate is None:
            return 1
        return sum(1 for n in self.flatten(tree) if predicate(n))

    def find_matches(self, tree: ElementNode, locator_type: str, value: str, limit: int = 50) -> List[ElementNode]:
        predicate = self.build_predicate(locator_type, value)
        if predicate is None:
            return []
        found: List[ElementNode] = []
        for n in self.flatten(tree):
            if predicate(n):
                found.append(n)
                if len(found) >= limit:
                    break
        return found

    def flatten(self, tree: ElementNode) -> List[ElementNode]:
        result = [tree]
        for child in tree.children:
            result.extend(self.flatten(child))
        return result

    def build_predicate(self, locator_type: str, value: str) -> Optional[Callable[[ElementNode], bool]]:
        t = locator_type.lower()
        if t in ("resource_id", "id"):
            return lambda n: n.resource_id == value
        if t == "text":
            return lambda n: n.text == value
        if t in ("content_desc", "accessibility_id"):
            return lambda n: (n.content_desc or n.accessibility_id) == value
        if t == "class_name":
            return lambda n: n.class_name == value
        if t in ("uiautomator2", "ui_automator", "composite", "instance"):
            return self._parse_u2_predicate(value) or self._parse_ui_selector_predicate(value)
        if t.startswith("xpath"):
            return self._parse_xpath_predicate(value)
        if t == "coordinate":
            return None
        return None

    def _parse_u2_predicate(self, value: str) -> Optional[Callable[[ElementNode], bool]]:
        inner = value
        if inner.startswith("d(") and inner.endswith(")"):
            inner = inner[2:-1]
        elif inner.startswith("new UiSelector()"):
            return self._parse_ui_selector_predicate(value)

        checks: List[Callable[[ElementNode], bool]] = []

        for m in re.finditer(r'resourceId(?:Contains|StartsWith|EndsWith|Matches)?="([^"]+)"', inner):
            pat = m.group(1)
            key = m.group(0)
            if "Contains" in key:
                checks.append(lambda n, p=pat: bool(n.resource_id and p in n.resource_id))
            elif "StartsWith" in key:
                checks.append(lambda n, p=pat: bool(n.resource_id and n.resource_id.startswith(p)))
            elif "EndsWith" in key:
                checks.append(lambda n, p=pat: bool(n.resource_id and n.resource_id.endswith(p)))
            elif "Matches" in key:
                checks.append(lambda n, p=pat: bool(n.resource_id and re.search(p, n.resource_id)))
            else:
                checks.append(lambda n, v=pat: n.resource_id == v or (n.resource_id or "").endswith("/" + v))

        for m in re.finditer(r'text(?:Contains|StartsWith|EndsWith|Matches)?="([^"]+)"', inner):
            pat = m.group(1)
            key = m.group(0)
            if "Contains" in key:
                checks.append(lambda n, p=pat: bool(n.text and p in n.text))
            elif "StartsWith" in key:
                checks.append(lambda n, p=pat: bool(n.text and n.text.startswith(p)))
            elif "EndsWith" in key:
                checks.append(lambda n, p=pat: bool(n.text and n.text.endswith(p)))
            elif "Matches" in key:
                checks.append(lambda n, p=pat: bool(n.text and re.search(p, n.text)))
            else:
                checks.append(lambda n, v=pat: n.text == v)

        for m in re.finditer(r'description(?:Contains|StartsWith|EndsWith|Matches)?="([^"]+)"', inner):
            pat = m.group(1)
            key = m.group(0)
            if "Contains" in key:
                checks.append(lambda n, p=pat: bool(n.content_desc and p in n.content_desc))
            elif "StartsWith" in key:
                checks.append(lambda n, p=pat: bool(n.content_desc and n.content_desc.startswith(p)))
            elif "EndsWith" in key:
                checks.append(lambda n, p=pat: bool(n.content_desc and n.content_desc.endswith(p)))
            elif "Matches" in key:
                checks.append(lambda n, p=pat: bool(n.content_desc and re.search(p, n.content_desc)))
            else:
                checks.append(lambda n, v=pat: n.content_desc == v)

        for m in re.finditer(r'className(?:Matches|Contains)?="([^"]+)"', inner):
            pat = m.group(1)
            key = m.group(0)
            if "Contains" in key:
                checks.append(lambda n, p=pat: bool(n.class_name and p in n.class_name))
            elif "Matches" in key:
                checks.append(lambda n, p=pat: bool(n.class_name and re.search(p, n.class_name)))
            else:
                checks.append(lambda n, v=pat: n.class_name == v)

        for m in re.finditer(r'packageName(?:Matches)?="([^"]+)"', inner):
            pat = m.group(1)
            if "Matches" in m.group(0):
                checks.append(lambda n, p=pat: bool(n.package and re.search(p, n.package)))
            else:
                checks.append(lambda n, v=pat: n.package == v)

        for m in re.finditer(r'instance=(\d+)', inner):
            idx = int(m.group(1))
            checks.append(lambda n, i=idx: n.instance == i)

        for m in re.finditer(r'index=(\d+)', inner):
            idx = int(m.group(1))
            checks.append(lambda n, i=idx: n.index == i)

        for attr in ("clickable", "enabled", "focused", "focusable", "checkable", "checked", "selected", "scrollable", "longClickable"):
            if re.search(rf'\b{attr}=True\b', inner):
                checks.append(lambda n, a=attr: bool(getattr(n, a, False)))

        if not checks and 'text="' in inner:
            m = re.search(r'text="([^"]+)"', inner)
            if m:
                v = m.group(1)
                checks.append(lambda n, val=v: n.text == val)

        if not checks:
            return None

        def combined(n: ElementNode) -> bool:
            return all(c(n) for c in checks)

        return combined

    def _parse_ui_selector_predicate(self, value: str) -> Optional[Callable[[ElementNode], bool]]:
        if "UiSelector" not in value:
            return None
        return self._parse_u2_predicate(value.replace("new UiSelector()", "").replace(".", ""))

    def _parse_xpath_predicate(self, xpath: str) -> Optional[Callable[[ElementNode], bool]]:
        checks: List[Callable[[ElementNode], bool]] = []

        for m in re.finditer(r"@resource-id='([^']+)'", xpath):
            v = m.group(1)
            checks.append(lambda n, val=v: n.resource_id == val)
        for m in re.finditer(r"contains\(@resource-id,'([^']+)'\)", xpath):
            v = m.group(1)
            checks.append(lambda n, val=v: bool(n.resource_id and val in n.resource_id))

        for m in re.finditer(r"@text='([^']+)'", xpath):
            v = m.group(1)
            checks.append(lambda n, val=v: n.text == val)
        for m in re.finditer(r"contains\(@text,'([^']+)'\)", xpath):
            v = m.group(1)
            checks.append(lambda n, val=v: bool(n.text and val in n.text))
        for m in re.finditer(r"starts-with\(@text,'([^']+)'\)", xpath):
            v = m.group(1)
            checks.append(lambda n, val=v: bool(n.text and n.text.startswith(val)))
        for m in re.finditer(r"substring\(@text[^)]+\)='([^']+)'\)", xpath):
            v = m.group(1)
            checks.append(lambda n, val=v: bool(n.text and n.text.endswith(val)))

        for m in re.finditer(r"@content-desc='([^']+)'", xpath):
            v = m.group(1)
            checks.append(lambda n, val=v: n.content_desc == val)
        for m in re.finditer(r"contains\(@content-desc,'([^']+)'\)", xpath):
            v = m.group(1)
            checks.append(lambda n, val=v: bool(n.content_desc and val in n.content_desc))

        for m in re.finditer(r"@class='([^']+)'", xpath):
            v = m.group(1)
            checks.append(lambda n, val=v: n.class_name == val or (n.class_name or "").endswith("." + val))

        for m in re.finditer(r"@clickable='true'", xpath):
            checks.append(lambda n: n.clickable)
        for m in re.finditer(r"@enabled='true'", xpath):
            checks.append(lambda n: n.enabled)

        if not checks:
            return None

        def combined(n: ElementNode) -> bool:
            return all(c(n) for c in checks)

        return combined
