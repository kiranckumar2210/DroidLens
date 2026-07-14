"""UIAutomator2 locator strategies and custom builder."""

from __future__ import annotations

import re
from typing import Callable, List, Optional

from inspectiq.domain.models import (
    CustomLocatorRequest,
    CustomLocatorResult,
    CustomLocatorRule,
    ElementNode,
    LocatorCandidate,
    LocatorType,
    Platform,
)
from inspectiq.engine.element_selector import SmartElementSelector
from inspectiq.locator.ranker import LocatorRanker


class UiAutomator2Strategy:
    """Generate uiautomator2 Python selector strings."""

    def generate(self, element: ElementNode) -> List[LocatorCandidate]:
        results = []
        d = self._u2_dict(element)
        if not d:
            return results

        expr = self._dict_to_u2(d)
        results.append(
            LocatorCandidate(
                locator_type=LocatorType.UIAUTOMATOR2,
                value=f"d({expr})",
                display_name="uiautomator2 selector",
                scores=LocatorRanker.base_scores(0.92, 0.90, 0.93),
                recommended=True,
                reason="Primary selector for Python uiautomator2 automation",
                framework_hint="uiautomator2",
            )
        )

        if element.resource_id:
            rid = element.resource_id
            short = rid.split("/")[-1] if "/" in rid else rid
            results.append(
                LocatorCandidate(
                    locator_type=LocatorType.UIAUTOMATOR2,
                    value=f'd(resourceId="{rid}")',
                    display_name="uiautomator2 resourceId",
                    scores=LocatorRanker.base_scores(0.93, 0.92, 0.94),
                    recommended=True,
                    reason="Stable resource-id — preferred for uiautomator2",
                    framework_hint="uiautomator2",
                )
            )
            if short != rid:
                results.append(
                    LocatorCandidate(
                        locator_type=LocatorType.UIAUTOMATOR2,
                        value=f'd(resourceId="{short}")',
                        display_name="uiautomator2 resourceId (short)",
                        scores=LocatorRanker.base_scores(0.85, 0.80, 0.88),
                        recommended=False,
                        reason="Short resource-id may match multiple apps",
                        framework_hint="uiautomator2",
                    )
                )

        if element.text:
            results.append(
                LocatorCandidate(
                    locator_type=LocatorType.UIAUTOMATOR2,
                    value=f'd(text="{element.text}")',
                    display_name="uiautomator2 text",
                    scores=LocatorRanker.base_scores(0.75, 0.70, 0.72),
                    recommended=False,
                    reason="Text may change with localization",
                    framework_hint="uiautomator2",
                )
            )
            results.append(
                LocatorCandidate(
                    locator_type=LocatorType.UIAUTOMATOR2,
                    value=f'd(textContains="{element.text[:20]}")',
                    display_name="uiautomator2 textContains",
                    scores=LocatorRanker.base_scores(0.68, 0.75, 0.65),
                    recommended=False,
                    reason="Partial text match for dynamic labels",
                    framework_hint="uiautomator2",
                )
            )

        if element.content_desc:
            results.append(
                LocatorCandidate(
                    locator_type=LocatorType.UIAUTOMATOR2,
                    value=f'd(description="{element.content_desc}")',
                    display_name="uiautomator2 description",
                    scores=LocatorRanker.base_scores(0.88, 0.85, 0.87),
                    recommended=True,
                    reason="Content-desc is stable accessibility identifier",
                    framework_hint="uiautomator2",
                )
            )

        if element.class_name:
            short = element.class_name.split(".")[-1]
            if element.instance > 0:
                results.append(
                    LocatorCandidate(
                        locator_type=LocatorType.INSTANCE,
                        value=f'd(className="{element.class_name}", instance={element.instance})',
                        display_name="uiautomator2 className + instance",
                        scores=LocatorRanker.base_scores(0.60, 0.85, 0.55),
                        recommended=False,
                        reason="Instance index when multiple same-class elements exist",
                        framework_hint="uiautomator2",
                    )
                )
            results.append(
                LocatorCandidate(
                    locator_type=LocatorType.CLASS_NAME,
                    value=f'd(className="{element.class_name}")',
                    display_name="uiautomator2 className",
                    scores=LocatorRanker.base_scores(0.55, 0.50, 0.50),
                    recommended=False,
                    reason="Class alone is rarely unique",
                    framework_hint="uiautomator2",
                )
            )

        return results

    def _u2_dict(self, element: ElementNode) -> dict:
        d = {}
        if element.resource_id:
            d["resourceId"] = element.resource_id
        if element.text:
            d["text"] = element.text
        if element.content_desc:
            d["description"] = element.content_desc
        if element.class_name and not d:
            d["className"] = element.class_name
        if element.clickable:
            d["clickable"] = True
        return d

    def _dict_to_u2(self, d: dict) -> str:
        parts = []
        for k, v in d.items():
            if isinstance(v, bool):
                parts.append(f'{k}={v}')
            else:
                parts.append(f'{k}="{v}"')
        return ", ".join(parts)


class CustomLocatorBuilder:
    """Build and validate custom locators from visual rules."""

    def __init__(self):
        self._selector = SmartElementSelector()

    def build(self, tree: ElementNode, request: CustomLocatorRequest) -> CustomLocatorResult:
        target_pred = self._rules_predicate(request.rules)
        xpath = self._to_xpath(request, target_pred)
        matched = self._match_with_context(tree, request, target_pred)
        u2 = self._to_u2(request)
        return CustomLocatorResult(
            xpath=xpath,
            uiautomator2=u2,
            match_count=len(matched),
            matched_elements=matched[:20],
        )

    def _attr_map(self) -> dict:
        return {
            "text": "text",
            "resource-id": "resource-id",
            "resource_id": "resource-id",
            "class": "class",
            "class_name": "class",
            "content-desc": "content-desc",
            "content_desc": "content-desc",
            "description": "content-desc",
            "package": "package",
            "clickable": "clickable",
            "enabled": "enabled",
        }

    def _to_xpath(self, request: CustomLocatorRequest, target_pred: str) -> str:
        predicate = target_pred if target_pred != "*" else "*"
        rel = request.relationship or request.axis

        if request.anchor_value and request.anchor_attribute:
            anchor = self._anchor_predicate(
                request.anchor_attribute,
                request.anchor_operator or "equals",
                request.anchor_value,
            )
            if rel in ("child_of", "child"):
                return f"//*[{anchor}]/*[{predicate}]"
            if rel in ("inside", "descendant", "ancestor"):
                return f"//*[{anchor}]//descendant::*[{predicate}]"
            if rel in ("sibling_after", "following", "after", "below"):
                return f"//*[{anchor}]/following-sibling::*[{predicate}]"
            if rel in ("sibling_before", "preceding", "before", "above"):
                return f"//*[{predicate}]/preceding-sibling::*[{anchor}]"
            if rel == "parent":
                return f"//*[{predicate}]/parent::*[{anchor}]"
            return f"//*[{anchor}]//*[{predicate}]"

        base = f"//*[{predicate}]"
        if rel == "parent":
            return f"{base}/parent::*"
        if rel == "child":
            return f"{base}/*"
        if rel == "sibling":
            return f"{base}/following-sibling::*[1]"
        if rel == "ancestor":
            return f"{base}/ancestor::*[1]"
        if rel == "descendant":
            return f"{base}//descendant::*"
        return base

    def _anchor_predicate(self, attr: str, op: str, value: str) -> str:
        attr_map = self._attr_map()
        mapped = attr_map.get(attr, attr)
        val = value.replace("'", "\\'")
        op = op.lower()
        if op == "equals":
            return f"@{mapped}='{val}'"
        if op == "contains":
            return f"contains(@{mapped},'{val}')"
        if op == "starts_with":
            return f"starts-with(@{mapped},'{val}')"
        if op == "ends_with":
            return f"substring(@{mapped}, string-length(@{mapped}) - {len(val)} + 1)='{val}'"
        if op == "regex":
            return f"matches(@{mapped},'{val}')"
        return f"@{mapped}='{val}'"

    def _rules_predicate(self, rules: List[CustomLocatorRule]) -> str:
        attr_map = self._attr_map()
        parts = []
        for rule in rules:
            attr = attr_map.get(rule.attribute, rule.attribute)
            val = rule.value.replace("'", "\\'")
            op = rule.operator.lower()
            if op == "equals":
                parts.append(f"@{attr}='{val}'")
            elif op == "contains":
                parts.append(f"contains(@{attr},'{val}')")
            elif op == "starts_with":
                parts.append(f"starts-with(@{attr},'{val}')")
            elif op == "ends_with":
                parts.append(f"substring(@{attr}, string-length(@{attr}) - {len(val)} + 1)='{val}'")
            elif op == "regex":
                parts.append(f"matches(@{attr},'{val}')")
        return " and ".join(parts) if parts else "*"

    def _to_u2(self, request: CustomLocatorRequest) -> str:
        u2_map = {
            "text": "text",
            "resource-id": "resourceId",
            "resource_id": "resourceId",
            "class": "className",
            "class_name": "className",
            "content-desc": "description",
            "content_desc": "description",
            "description": "description",
        }
        parts = []
        for rule in request.rules:
            key = u2_map.get(rule.attribute)
            if not key:
                continue
            val = rule.value.replace('"', '\\"')
            op = rule.operator.lower()
            if op == "equals":
                parts.append(f'{key}="{val}"')
            elif op == "contains":
                parts.append(f'{key}Contains="{val}"')
            elif op == "starts_with":
                parts.append(f'{key}StartsWith="{val}"')
            elif op == "ends_with":
                parts.append(f'{key}EndsWith="{val}"')
            elif op == "regex":
                parts.append(f'{key}Matches="{val}"')

        target = f"d({', '.join(parts)})" if parts else "d()"

        if request.anchor_value and request.anchor_attribute:
            anchor_key = u2_map.get(request.anchor_attribute, request.anchor_attribute)
            aval = request.anchor_value.replace('"', '\\"')
            anchor = f'd({anchor_key}="{aval}")'
            rel = request.relationship or request.axis
            if rel in ("child_of", "child"):
                return f"{anchor}.child({', '.join(parts)})"
            if rel in ("sibling_after", "following", "after"):
                return f"{anchor}.sibling({', '.join(parts)})"
            if rel in ("inside", "descendant"):
                return f"{anchor}.child({', '.join(parts)})"
        return target

    def _match_with_context(
        self,
        tree: ElementNode,
        request: CustomLocatorRequest,
        target_pred: str,
    ) -> List[ElementNode]:
        flat = self._selector.flatten(tree)
        target_matches = [n for n in flat if self._node_matches_rules(n, request.rules)]

        if not request.anchor_value or not request.anchor_attribute:
            return target_matches

        anchor_rules = [
            CustomLocatorRule(
                attribute=request.anchor_attribute,
                operator=request.anchor_operator or "equals",
                value=request.anchor_value,
            )
        ]
        anchors = [n for n in flat if self._node_matches_rules(n, anchor_rules)]
        if not anchors:
            return []

        rel = request.relationship or request.axis or "inside"
        results: List[ElementNode] = []
        for anchor in anchors:
            for target in target_matches:
                if rel in ("child_of", "child") and target.parent_id == anchor.id:
                    results.append(target)
                elif rel in ("inside", "descendant", "ancestor"):
                    if self._is_descendant(anchor, target, tree):
                        results.append(target)
                elif rel in ("sibling_after", "following", "after", "below"):
                    if self._is_following_sibling(anchor, target, tree):
                        results.append(target)
                elif rel in ("sibling_before", "preceding", "before", "above"):
                    if self._is_preceding_sibling(anchor, target, tree):
                        results.append(target)
        return results

    def _is_descendant(self, ancestor: ElementNode, node: ElementNode, tree: ElementNode) -> bool:
        path = self._selector.get_path_to_element(tree, node)
        return path is not None and any(a.id == ancestor.id for a in path)

    def _is_following_sibling(self, anchor: ElementNode, target: ElementNode, tree: ElementNode) -> bool:
        parent = self._selector.get_parent(tree, anchor)
        if not parent or target.parent_id != parent.id:
            return False
        seen_anchor = False
        for child in parent.children:
            if child.id == anchor.id:
                seen_anchor = True
                continue
            if seen_anchor and child.id == target.id:
                return True
        return False

    def _is_preceding_sibling(self, anchor: ElementNode, target: ElementNode, tree: ElementNode) -> bool:
        parent = self._selector.get_parent(tree, anchor)
        if not parent or target.parent_id != parent.id:
            return False
        for child in parent.children:
            if child.id == target.id:
                return True
            if child.id == anchor.id:
                return False
        return False

    def _node_matches_rules(self, node: ElementNode, rules: List[CustomLocatorRule]) -> bool:
        attr_map = self._attr_map()
        for rule in rules:
            attr = attr_map.get(rule.attribute, rule.attribute)
            val = self._get_attr(node, attr)
            if val is None:
                return False
            op = rule.operator.lower()
            if op == "equals" and val != rule.value:
                return False
            if op == "contains" and rule.value not in val:
                return False
            if op == "starts_with" and not val.startswith(rule.value):
                return False
            if op == "ends_with" and not val.endswith(rule.value):
                return False
            if op == "regex" and not re.search(rule.value, val):
                return False
        return True

    def _get_attr(self, node: ElementNode, attr: str) -> Optional[str]:
        mapping = {
            "text": node.text,
            "resource-id": node.resource_id,
            "class": node.class_name,
            "content-desc": node.content_desc,
            "package": node.package,
            "clickable": str(node.clickable).lower(),
            "enabled": str(node.enabled).lower(),
        }
        v = mapping.get(attr)
        return str(v) if v is not None else None
