"""Context-aware relative locator generation."""

from __future__ import annotations

from typing import List, Optional

from inspectiq.domain.models import ElementNode, LocatorCandidate, LocatorType, XPathExample
from inspectiq.engine.element_selector import SmartElementSelector
from inspectiq.locator.ranker import LocatorRanker


def _esc(s: str) -> str:
    return s.replace("'", "\\'")


class RelativeLocatorEngine:
    """Generate relationship-based locators using hierarchy context."""

    def __init__(self):
        self._selector = SmartElementSelector()

    def generate_relative_locators(self, element: ElementNode, tree: ElementNode) -> List[LocatorCandidate]:
        ctx = self._selector.get_context(tree, element)
        parent = ctx["parent"]
        results: List[LocatorCandidate] = []

        results.extend(self._parent_child_locators(element, parent))
        results.extend(self._sibling_locators(element, ctx))
        results.extend(self._ancestor_locators(element, tree))
        results.extend(self._positional_locators(element, ctx))
        return results

    def generate_relative_xpaths(self, element: ElementNode, tree: ElementNode) -> List[XPathExample]:
        examples: List[XPathExample] = []
        ctx = self._selector.get_context(tree, element)
        parent = ctx["parent"]
        el_xpath = self._element_predicate(element)

        if parent:
            parent_pred = self._node_predicate(parent)
            if parent_pred:
                examples.append(XPathExample(
                    axis="child",
                    xpath=f"//*[{parent_pred}]/*[{el_xpath}]",
                    description="Direct child of identified parent",
                ))
                examples.append(XPathExample(
                    axis="descendant",
                    xpath=f"//*[{parent_pred}]//descendant::*[{el_xpath}]",
                    description="Descendant inside parent container",
                ))
                examples.append(XPathExample(
                    axis="parent",
                    xpath=f"//*[{el_xpath}]/parent::*",
                    description="Parent of selected element",
                ))

        if ctx["siblings_before"]:
            sib = ctx["siblings_before"][-1]
            sib_pred = self._node_predicate(sib)
            if sib_pred:
                examples.append(XPathExample(
                    axis="following-sibling",
                    xpath=f"//*[{sib_pred}]/following-sibling::*[{el_xpath}]",
                    description="Element following identified sibling",
                ))
                examples.append(XPathExample(
                    axis="preceding-sibling",
                    xpath=f"//*[{el_xpath}]/preceding-sibling::*[{sib_pred}]",
                    description="Preceding sibling reference",
                ))

        if ctx["siblings_after"]:
            sib = ctx["siblings_after"][0]
            sib_pred = self._node_predicate(sib)
            if sib_pred and sib.text:
                examples.append(XPathExample(
                    axis="context",
                    xpath=f"//*[@text='{_esc(sib.text)}']/preceding-sibling::*[{el_xpath}]",
                    description=f"Element before sibling '{sib.text[:20]}'",
                ))

        if element.children:
            examples.append(XPathExample(
                axis="first-child",
                xpath=f"//*[{el_xpath}]/*[1]",
                description="First direct child",
            ))
            examples.append(XPathExample(
                axis="last-child",
                xpath=f"//*[{el_xpath}]/*[last()]",
                description="Last direct child",
            ))

        idx = self._child_index(parent, element) if parent else None
        if idx is not None and parent:
            pp = self._node_predicate(parent)
            if pp:
                examples.append(XPathExample(
                    axis="nth-child",
                    xpath=f"//*[{pp}]/*[{idx}]",
                    description=f"Nth child (position {idx}) under parent",
                ))

        # Hierarchy-relative path (compact, not absolute from root)
        rel_path = self._compact_hierarchy_path(tree, element)
        if rel_path:
            examples.append(XPathExample(
                axis="relative-path",
                xpath=rel_path,
                description="Compact hierarchy-relative XPath",
            ))

        return examples

    def _parent_child_locators(self, element: ElementNode, parent: Optional[ElementNode]) -> List[LocatorCandidate]:
        if not parent:
            return []
        results = []
        anchor = self._anchor_label(parent)
        target = self._target_fragment(element)
        if not anchor or not target:
            return []

        xpath = f"//*[{anchor}]/*[{target}]"
        u2_anchor = self._u2_anchor(parent)
        u2 = f"{u2_anchor}.child({self._u2_target(element)})" if u2_anchor else f"d({self._u2_target(element)})"

        results.append(LocatorCandidate(
            locator_type=LocatorType.XPATH_RELATIVE,
            value=xpath,
            display_name=f"Child of {self._short_label(parent)}",
            scores=LocatorRanker.base_scores(0.72, 0.80, 0.68),
            recommended=False,
            reason=f"Direct child under {self._short_label(parent)} — stable when container is unique",
            export_formats={"xpath": xpath, "uiautomator2": u2},
        ))

        xpath_desc = f"//*[{anchor}]//descendant::*[{target}]"
        results.append(LocatorCandidate(
            locator_type=LocatorType.XPATH_RELATIVE,
            value=xpath_desc,
            display_name=f"Descendant of {self._short_label(parent)}",
            scores=LocatorRanker.base_scores(0.68, 0.75, 0.65),
            recommended=False,
            reason=f"Descendant inside {self._short_label(parent)}",
            export_formats={"xpath": xpath_desc},
        ))
        return results

    def _sibling_locators(self, element: ElementNode, ctx: dict) -> List[LocatorCandidate]:
        results = []
        for label, siblings, rel, axis_name in [
            ("following", ctx["siblings_after"][:1], "following-sibling", "Next sibling context"),
            ("preceding", ctx["siblings_before"][-1:], "preceding-sibling", "Previous sibling context"),
        ]:
            for sib in siblings:
                anchor = self._node_predicate(sib)
                target = self._element_predicate(element)
                if not anchor:
                    continue
                if rel == "following-sibling":
                    xpath = f"//*[{anchor}]/following-sibling::*[{target}]"
                else:
                    xpath = f"//*[{target}]/preceding-sibling::*[{anchor}]"
                results.append(LocatorCandidate(
                    locator_type=LocatorType.XPATH_RELATIVE,
                    value=xpath,
                    display_name=f"{axis_name}: {self._short_label(sib)}",
                    scores=LocatorRanker.base_scores(0.62, 0.72, 0.58),
                    recommended=False,
                    reason=f"Positional relationship to '{self._short_label(sib)}'",
                    export_formats={"xpath": xpath},
                ))

        if ctx["siblings_before"]:
            sib = ctx["siblings_before"][-1]
            if sib.text and element.text:
                xpath = f"//*[@text='{_esc(sib.text)}']/following-sibling::*[@text='{_esc(element.text)}']"
                results.append(LocatorCandidate(
                    locator_type=LocatorType.COMPOSITE,
                    value=f"d(text=\"{_esc(sib.text)}\").sibling({self._u2_target(element)})",
                    display_name=f"After '{sib.text[:15]}'",
                    scores=LocatorRanker.base_scores(0.70, 0.78, 0.62),
                    recommended=False,
                    reason=f"Element following sibling with text '{sib.text[:20]}'",
                    export_formats={"xpath": xpath},
                ))
        return results

    def _ancestor_locators(self, element: ElementNode, tree: ElementNode) -> List[LocatorCandidate]:
        results = []
        ancestors = self._selector.get_ancestors(tree, element)
        for anc in ancestors[:3]:
            anchor = self._node_predicate(anc)
            target = self._element_predicate(element)
            if not anchor:
                continue
            xpath = f"//*[{anchor}]//descendant::*[{target}]"
            results.append(LocatorCandidate(
                locator_type=LocatorType.XPATH_RELATIVE,
                value=xpath,
                display_name=f"Inside {self._short_label(anc)}",
                scores=LocatorRanker.base_scores(0.65, 0.70, 0.60),
                recommended=False,
                reason=f"Descendant of ancestor {self._short_label(anc)}",
                export_formats={"xpath": xpath},
            ))
        return results

    def _positional_locators(self, element: ElementNode, ctx: dict) -> List[LocatorCandidate]:
        results = []
        if not element.bounds:
            return results
        y = element.bounds.center_y
        if ctx["siblings_before"]:
            for sib in ctx["siblings_before"][-2:]:
                if sib.bounds and sib.text:
                    if sib.bounds.center_y < y:
                        el_text = _esc(element.text or "")
                        xpath = f"//*[@text='{_esc(sib.text)}']/following-sibling::*[@text='{el_text}']"
                        results.append(LocatorCandidate(
                            locator_type=LocatorType.XPATH_RELATIVE,
                            value=xpath,
                            display_name=f"Below '{sib.text[:12]}'",
                            scores=LocatorRanker.base_scores(0.60, 0.68, 0.55),
                            recommended=False,
                            reason=f"Visually below '{sib.text[:20]}' (following sibling)",
                            export_formats={"xpath": xpath},
                        ))
        return results

    def _compact_hierarchy_path(self, tree: ElementNode, target: ElementNode) -> Optional[str]:
        path = self._selector.get_path_to_element(tree, target)
        if not path or len(path) < 2:
            return None
        segments = []
        for node in path[-4:]:
            short = node.class_name.split(".")[-1] if node.class_name else "*"
            pred = self._node_predicate(node)
            if pred:
                segments.append(f"{short}[{pred}]")
            else:
                segments.append(short)
        return "//" + "/".join(segments)

    @staticmethod
    def _short_label(node: ElementNode) -> str:
        return node.text or (node.resource_id.split("/")[-1] if node.resource_id else None) or node.class_name.split(".")[-1] or "element"

    def _node_predicate(self, node: ElementNode) -> Optional[str]:
        if node.resource_id:
            return f"@resource-id='{_esc(node.resource_id)}'"
        if node.text:
            return f"@text='{_esc(node.text)}'"
        if node.content_desc:
            return f"@content-desc='{_esc(node.content_desc)}'"
        if node.class_name:
            return f"@class='{_esc(node.class_name)}'"
        return None

    def _element_predicate(self, element: ElementNode) -> str:
        return self._node_predicate(element) or "@clickable='true'"

    def _anchor_label(self, node: ElementNode) -> Optional[str]:
        return self._node_predicate(node)

    def _target_fragment(self, element: ElementNode) -> str:
        return self._element_predicate(element)

    def _u2_anchor(self, node: ElementNode) -> Optional[str]:
        if node.resource_id:
            return f'd(resourceId="{node.resource_id}")'
        if node.text:
            return f'd(text="{_esc(node.text)}")'
        if node.content_desc:
            return f'd(description="{_esc(node.content_desc)}")'
        return None

    def _u2_target(self, element: ElementNode) -> str:
        parts = []
        if element.resource_id:
            parts.append(f'resourceId="{element.resource_id}"')
        elif element.text:
            parts.append(f'text="{_esc(element.text)}"')
        elif element.content_desc:
            parts.append(f'description="{_esc(element.content_desc)}"')
        elif element.class_name:
            parts.append(f'className="{element.class_name}"')
        if element.clickable:
            parts.append("clickable=True")
        return ", ".join(parts) if parts else 'className="*"'

    @staticmethod
    def _child_index(parent: ElementNode, child: ElementNode) -> Optional[int]:
        for i, c in enumerate(parent.children, start=1):
            if c.id == child.id:
                return i
        return None
