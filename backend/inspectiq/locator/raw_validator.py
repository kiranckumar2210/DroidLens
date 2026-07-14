"""Validate raw XPath / UiSelector locators against session tree."""

from __future__ import annotations

import time

from inspectiq.domain.models import ElementNode
from inspectiq.locator.locator_matcher import LocatorMatcher


class RawLocatorValidator:
    def __init__(self):
        self._matcher = LocatorMatcher()

    def validate(
        self,
        tree: ElementNode,
        locator_type: str,
        expression: str,
    ) -> dict:
        expression = expression.strip()
        if not expression:
            return {"valid": False, "match_count": 0, "error": "Empty expression", "matched_ids": []}

        t0 = time.monotonic()
        try:
            mapped_type = self._map_type(locator_type, expression)
            matched = self._matcher.find_matches(tree, mapped_type, expression, limit=50)
            count = len(matched) if matched else self._matcher.count_matches(tree, mapped_type, expression)
            if matched:
                count = self._matcher.count_matches(tree, mapped_type, expression)
        except Exception as exc:
            return {"valid": False, "match_count": 0, "error": str(exc), "matched_ids": []}

        elapsed_ms = round((time.monotonic() - t0) * 1000, 3)
        warning = None
        recommendation = None
        if count == 0:
            warning = "No elements matched"
            recommendation = "Refine expression or verify the UI hierarchy is current"
        elif count > 1:
            warning = f"{count} elements matched — locator may be ambiguous"
            recommendation = "Add resource-id, text, or parent context to narrow matches"
        else:
            recommendation = "Unique match — locator is reliable for this tree"

        reliability = 100 if count == 1 else (max(10, int(100 / count)) if count > 1 else 0)

        return {
            "valid": count > 0,
            "match_count": count,
            "unique": count == 1,
            "reliability_score": reliability,
            "execution_ms": elapsed_ms,
            "recommendation": recommendation,
            "warning": warning,
            "error": None if count > 0 else "No matches",
            "matched_ids": [n.id for n in matched[:50]],
            "matched_elements": matched[:10],
        }

    @staticmethod
    def _map_type(locator_type: str, expression: str) -> str:
        t = locator_type.lower()
        if t in ("xpath", "relative_xpath"):
            return "xpath"
        if t in ("uiselector", "ui_automator", "uiautomator2"):
            if expression.strip().startswith("d("):
                return "uiautomator2"
            return "ui_automator"
        return t
