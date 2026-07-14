"""Intelligent multi-strategy locator engine — orchestrates generation, ranking, and suggestions."""

from __future__ import annotations

import hashlib
import re
import time
from typing import Dict, List, Optional, Set, Tuple

from inspectiq.domain.models import (
    ElementAnalysisContext,
    ElementNode,
    LocatorBadge,
    LocatorBundle,
    LocatorCandidate,
    LocatorCategory,
    LocatorComparisonResult,
    LocatorGroup,
    LocatorScore,
    LocatorSuggestion,
    LocatorType,
    Platform,
    XPathExample,
)
from inspectiq.engine.element_selector import SmartElementSelector
from inspectiq.locator.expanded_generators import ExpandedAndroidGenerator, _dynamic_id
from inspectiq.locator.locator_matcher import LocatorMatcher
from inspectiq.locator.ranker import LocatorRanker
from inspectiq.locator.relative_engine import RelativeLocatorEngine
from inspectiq.locator.strategies import ALL_STRATEGIES
from inspectiq.locator.xpath_builder import XPathBuilder


_CATEGORY_LABELS: Dict[str, str] = {
    LocatorCategory.RESOURCE_ID.value: "Resource ID",
    LocatorCategory.ACCESSIBILITY.value: "Accessibility",
    LocatorCategory.TEXT.value: "Text",
    LocatorCategory.CLASS_NAME.value: "Class",
    LocatorCategory.PACKAGE.value: "Package",
    LocatorCategory.INDEX.value: "Index",
    LocatorCategory.UISELECTOR.value: "UiSelector",
    LocatorCategory.XPATH.value: "XPath",
    LocatorCategory.RELATIVE.value: "Relative",
    LocatorCategory.COMBINED.value: "Combined",
    LocatorCategory.ADVANCED_XPATH.value: "Advanced XPath",
    LocatorCategory.COORDINATE.value: "Coordinate",
    LocatorCategory.OTHER.value: "Other",
}

_CATEGORY_ORDER = list(_CATEGORY_LABELS.keys())

_VOLATILE_TEXT = re.compile(r"\d{2,}|%|\$|€|£|₹")


class LocatorEngine:
    """Orchestrates locator generation, uniqueness validation, ranking, and caching."""

    MAX_CANDIDATES = 100
    CACHE_MAX = 64

    def __init__(self) -> None:
        self._selector = SmartElementSelector()
        self._matcher = LocatorMatcher()
        self._expanded = ExpandedAndroidGenerator()
        self._relative = RelativeLocatorEngine()
        self._xpath = XPathBuilder()
        self._cache: Dict[str, LocatorBundle] = {}

    def generate_bundle(self, element: ElementNode, tree: ElementNode) -> LocatorBundle:
        cache_key = self._cache_key(element, tree)
        if cache_key in self._cache:
            return self._cache[cache_key]

        t0 = time.monotonic()
        analysis = self.analyze_element(element, tree)
        candidates = self._collect_candidates(element, tree)
        candidates = self._filter_redundant_composites(candidates, tree)
        for loc in candidates:
            self._enrich(loc, tree, element, analysis)
        candidates.sort(key=lambda c: (c.recommended, c.scores.overall), reverse=True)
        self._apply_recommendations(candidates)
        candidates = candidates[: self.MAX_CANDIDATES]

        groups = self._group_locators(candidates)
        suggestions = self.generate_suggestions(element, tree, analysis, candidates)
        recommended = next((c for c in candidates if c.recommended), candidates[0] if candidates else None)
        xpath_examples = self._xpath.build_all(element, tree)

        bundle = LocatorBundle(
            element=element,
            analysis=analysis,
            groups=groups,
            all_locators=candidates,
            suggestions=suggestions,
            recommended=recommended,
            xpath_examples=xpath_examples,
            generation_ms=round((time.monotonic() - t0) * 1000, 2),
            tree_hash=cache_key.split(":")[0],
        )
        self._store_cache(cache_key, bundle)
        return bundle

    def generate_all(self, element: ElementNode, tree: ElementNode) -> List[LocatorCandidate]:
        return self.generate_bundle(element, tree).all_locators

    def analyze_element(self, element: ElementNode, tree: ElementNode) -> ElementAnalysisContext:
        ctx = self._selector.get_context(tree, element)
        ancestors = self._selector.get_ancestors(tree, element)
        siblings = ctx["siblings_before"] + ctx["siblings_after"]
        parent = ctx["parent"]
        stable: List[str] = []
        if element.resource_id and not _dynamic_id(element.resource_id):
            stable.append("resource_id")
        if element.content_desc or element.accessibility_id:
            stable.append("accessibility")
        if element.text and not self._is_dynamic_text(element.text):
            stable.append("text")

        rid_dupes = 0
        if element.resource_id:
            rid_dupes = sum(
                1 for n in self._matcher.flatten(tree)
                if n.resource_id == element.resource_id and n.id != element.id
            )

        in_recycler = any(
            "RecyclerView" in (a.class_name or "") for a in ancestors
        )
        in_scroll = any(a.scrollable for a in ancestors)

        return ElementAnalysisContext(
            element_id=element.id,
            hierarchy_level=element.depth,
            ancestor_count=len(ancestors),
            sibling_count=len(siblings),
            child_count=len(ctx["children"]),
            parent_class=parent.class_name if parent else None,
            parent_resource_id=parent.resource_id if parent else None,
            is_in_recyclerview=in_recycler,
            is_in_scrollable=in_scroll,
            has_dynamic_text=bool(element.text and self._is_dynamic_text(element.text)),
            has_dynamic_resource_id=bool(element.resource_id and _dynamic_id(element.resource_id)),
            duplicate_resource_ids_in_tree=rid_dupes,
            stable_attributes=stable,
        )

    def generate_suggestions(
        self,
        element: ElementNode,
        tree: ElementNode,
        analysis: ElementAnalysisContext,
        locators: List[LocatorCandidate],
    ) -> List[LocatorSuggestion]:
        tips: List[LocatorSuggestion] = []

        if not element.resource_id and not element.content_desc:
            tips.append(LocatorSuggestion(
                severity="warning",
                category="stability",
                message="No resource-id or accessibility identifier on this element.",
                hint="Prefer parent-relative locators or coordinate fallback for custom views.",
            ))
        elif element.resource_id:
            tips.append(LocatorSuggestion(
                severity="info",
                category="best_practice",
                message="Resource ID is the preferred Android locator strategy.",
                hint="Use resourceId() or AppiumBy.ID when unique.",
            ))

        if analysis.has_dynamic_text:
            tips.append(LocatorSuggestion(
                severity="warning",
                category="dynamic_text",
                message="Text appears dynamic (numbers, currency, or long content).",
                hint="Use textContains/textStartsWith or combine text with resource-id.",
            ))

        if analysis.has_dynamic_resource_id:
            tips.append(LocatorSuggestion(
                severity="warning",
                category="dynamic_id",
                message="Resource ID looks generated or unstable.",
                hint="Avoid bare resource-id; use composite or relative locators.",
            ))

        if analysis.duplicate_resource_ids_in_tree > 0:
            tips.append(LocatorSuggestion(
                severity="warning",
                category="duplicate_rid",
                message=f"Resource ID shared by {analysis.duplicate_resource_ids_in_tree + 1} elements in tree.",
                hint="Combine with text, class, or parent-relative XPath.",
            ))

        index_locs = [l for l in locators if l.category == LocatorCategory.INDEX.value or "index" in l.display_name.lower()]
        if index_locs and any(l.recommended for l in index_locs):
            tips.append(LocatorSuggestion(
                severity="warning",
                category="index",
                message="Index-based locators are fragile when list order changes.",
                hint="Use instance only as last resort when duplicates share attributes.",
            ))
        elif index_locs:
            tips.append(LocatorSuggestion(
                severity="info",
                category="index",
                message="Index/instance locators available but marked low reliability.",
                hint="Prefer semantic locators when possible.",
            ))

        if analysis.is_in_recyclerview:
            tips.append(LocatorSuggestion(
                severity="info",
                category="recyclerview",
                message="Element is inside a RecyclerView.",
                hint="Use scroll-into-view + resource-id or parent-relative locator.",
            ))

        non_unique = [l for l in locators if l.is_duplicate]
        if non_unique:
            tips.append(LocatorSuggestion(
                severity="warning",
                category="uniqueness",
                message=f"{len(non_unique)} generated locator(s) match multiple elements.",
                hint="Review locators flagged as ambiguous or use composite strategies.",
            ))

        if not any(l.recommended for l in locators):
            tips.append(LocatorSuggestion(
                severity="warning",
                category="fallback",
                message="No strongly recommended locator — consider coordinate tap or custom builder.",
            ))

        return tips

    def compare_locators(
        self,
        tree: ElementNode,
        locator_a: LocatorCandidate,
        locator_b: LocatorCandidate,
    ) -> LocatorComparisonResult:
        matches_a = self._matcher.count_matches(tree, locator_a.locator_type.value, locator_a.value)
        matches_b = self._matcher.count_matches(tree, locator_b.locator_type.value, locator_b.value)
        set_a = {n.id for n in self._matcher.find_matches(tree, locator_a.locator_type.value, locator_a.value, limit=100)}
        set_b = {n.id for n in self._matcher.find_matches(tree, locator_b.locator_type.value, locator_b.value, limit=100)}
        overlap = len(set_a & set_b)

        perf_order = {"fast": 3, "medium": 2, "slow": 1}
        pa = perf_order.get(locator_a.performance_rating or "medium", 2)
        pb = perf_order.get(locator_b.performance_rating or "medium", 2)
        faster = "a" if pa > pb else ("b" if pb > pa else None)
        more_stable = "a" if locator_a.scores.stability > locator_b.scores.stability else (
            "b" if locator_b.scores.stability > locator_a.scores.stability else None
        )

        rec_parts = []
        if matches_a == 1 and matches_b != 1:
            rec_parts.append("Locator A is unique.")
        elif matches_b == 1 and matches_a != 1:
            rec_parts.append("Locator B is unique.")
        if locator_a.scores.overall > locator_b.scores.overall + 0.05:
            rec_parts.append("Locator A scores higher overall.")
        elif locator_b.scores.overall > locator_a.scores.overall + 0.05:
            rec_parts.append("Locator B scores higher overall.")
        recommendation = " ".join(rec_parts) if rec_parts else "Both locators are comparable — prefer the unique one."

        return LocatorComparisonResult(
            locator_a=locator_a,
            locator_b=locator_b,
            matches_a=matches_a,
            matches_b=matches_b,
            overlap_count=overlap,
            faster=faster,
            more_stable=more_stable,
            recommendation=recommendation,
        )

    def preview(self, tree: ElementNode, locator_type: str, value: str) -> dict:
        t0 = time.monotonic()
        matched = self._matcher.find_matches(tree, locator_type, value, limit=50)
        count = self._matcher.count_matches(tree, locator_type, value)
        elapsed_ms = round((time.monotonic() - t0) * 1000, 3)
        return {
            "match_count": count,
            "valid": count > 0,
            "unique": count == 1,
            "matched_ids": [n.id for n in matched],
            "execution_ms": elapsed_ms,
            "warning": None if count == 1 else (f"{count} matches — ambiguous" if count > 1 else "No matches"),
            "recommendation": "Unique match — good locator" if count == 1 else (
                "Consider a more specific locator" if count > 1 else "No elements matched"
            ),
        }

    def _collect_candidates(self, element: ElementNode, tree: ElementNode) -> List[LocatorCandidate]:
        candidates: List[LocatorCandidate] = []
        seen: Set[Tuple[str, str]] = set()

        def add(loc: LocatorCandidate) -> None:
            key = (loc.locator_type.value, loc.value)
            if key in seen:
                return
            seen.add(key)
            candidates.append(loc)

        for strategy in ALL_STRATEGIES:
            if not strategy.supports(element.platform):
                continue
            for loc in strategy.generate(element):
                add(loc)

        if element.platform == Platform.ANDROID:
            for loc in self._expanded.generate_all(element):
                add(loc)
            for loc in self._relative.generate_relative_locators(element, tree):
                add(loc)

        for ex in self._xpath.build_all(element, tree):
            add(self._xpath_example_to_candidate(ex))

        shortest = self._shortest_unique_xpath(element, tree)
        if shortest:
            add(shortest)

        absolute = self._absolute_xpath(element, tree)
        if absolute:
            add(absolute)

        return candidates

    def _xpath_example_to_candidate(self, ex: XPathExample) -> LocatorCandidate:
        if ex.axis == "absolute":
            score = LocatorRanker.base_scores(0.30, 0.90, 0.25)
            recommended = False
            reason = "Breaks when UI hierarchy changes — avoid for maintenance"
            loc_type = LocatorType.XPATH
        elif ex.axis in ("contains", "starts-with", "ends-with"):
            score = LocatorRanker.base_scores(0.70, 0.75, 0.65)
            recommended = ex.axis == "contains"
            reason = "Partial match — useful when text is dynamic"
            loc_type = LocatorType.XPATH_CONTAINS if ex.axis == "contains" else (
                LocatorType.XPATH_STARTS_WITH if ex.axis == "starts-with" else LocatorType.XPATH_ENDS_WITH
            )
        elif ex.axis == "exact":
            score = LocatorRanker.base_scores(0.72, 0.88, 0.60)
            recommended = True
            reason = "Attribute-based XPath — acceptable when IDs unavailable"
            loc_type = LocatorType.XPATH
        elif ex.axis in ("relative-path", "child", "descendant", "parent", "following-sibling", "preceding-sibling", "nth-child", "first-child", "last-child", "context"):
            score = LocatorRanker.base_scores(0.65, 0.78, 0.62)
            recommended = False
            reason = f"Relative XPath ({ex.axis}) — stable when anchor is unique"
            loc_type = LocatorType.XPATH_RELATIVE
        elif ex.axis == "composite":
            score = LocatorRanker.base_scores(0.78, 0.85, 0.70)
            recommended = True
            reason = "Multi-attribute XPath combination"
            loc_type = LocatorType.XPATH
        else:
            score = LocatorRanker.base_scores(0.55, 0.70, 0.50)
            recommended = False
            reason = f"Axis-based XPath ({ex.axis}) — use for navigation, not primary locator"
            loc_type = LocatorType.XPATH_AXIS

        return LocatorCandidate(
            locator_type=loc_type,
            value=ex.xpath,
            display_name=f"XPath ({ex.axis})",
            scores=score,
            recommended=recommended,
            reason=reason,
            framework_hint="AppiumBy.XPATH",
        )

    def _absolute_xpath(self, element: ElementNode, tree: ElementNode) -> Optional[LocatorCandidate]:
        path = self._selector.get_path_to_element(tree, element)
        if not path:
            return None
        segments: List[str] = []
        for i, node in enumerate(path):
            tag = node.class_name.split(".")[-1] if node.class_name else "*"
            if i == 0:
                segments.append(tag)
                continue
            parent = path[i - 1]
            idx = 1
            for j, c in enumerate(parent.children, start=1):
                if c.id == node.id:
                    idx = j
                    break
            segments.append(f"{tag}[{idx}]")
        xpath = "/" + "/".join(segments)
        return LocatorCandidate(
            locator_type=LocatorType.XPATH,
            value=xpath,
            display_name="XPath (absolute)",
            scores=LocatorRanker.base_scores(0.28, 0.95, 0.22),
            recommended=False,
            reason="Absolute hierarchy path — avoid; breaks on any layout change",
            framework_hint="AppiumBy.XPATH",
        )

    @staticmethod
    def _child_index_in_parent(path: List[ElementNode], node: ElementNode) -> Optional[int]:
        for i, n in enumerate(path):
            if n.id != node.id or i == 0:
                continue
            parent = path[i - 1]
            for j, c in enumerate(parent.children, start=1):
                if c.id == node.id:
                    return j
        return None

    def _shortest_unique_xpath(self, element: ElementNode, tree: ElementNode) -> Optional[LocatorCandidate]:
        """Build the shortest attribute XPath that uniquely identifies the element."""
        attrs: List[Tuple[str, str, str]] = []
        if element.resource_id:
            attrs.append(("resource-id", element.resource_id, "exact"))
        if element.text:
            attrs.append(("text", element.text, "exact"))
            if len(element.text) > 3:
                attrs.append(("text", element.text[:10], "starts-with"))
        if element.content_desc:
            attrs.append(("content-desc", element.content_desc, "exact"))
        if element.class_name:
            attrs.append(("class", element.class_name, "exact"))

        best: Optional[Tuple[str, int]] = None
        for attr, val, mode in attrs:
            if mode == "exact":
                xpath = f"//*[@{attr}='{self._esc(val)}']"
            else:
                xpath = f"//*[starts-with(@{attr},'{self._esc(val)}')]"
            count = self._matcher.count_matches(tree, "xpath", xpath)
            if count == 1 and (best is None or len(xpath) < best[1]):
                best = (xpath, len(xpath))

        if len(attrs) >= 2:
            for i in range(len(attrs)):
                for j in range(i + 1, len(attrs)):
                    a1, v1, m1 = attrs[i]
                    a2, v2, _m2 = attrs[j]
                    p1 = f"@{a1}='{self._esc(v1)}'" if m1 == "exact" else f"starts-with(@{a1},'{self._esc(v1)}')"
                    p2 = f"@{a2}='{self._esc(v2)}'"
                    xpath = f"//*[{p1} and {p2}]"
                    count = self._matcher.count_matches(tree, "xpath", xpath)
                    if count == 1 and (best is None or len(xpath) < best[1]):
                        best = (xpath, len(xpath))

        if not best:
            return None
        return LocatorCandidate(
            locator_type=LocatorType.XPATH,
            value=best[0],
            display_name="XPath (shortest unique)",
            scores=LocatorRanker.base_scores(0.82, 0.95, 0.78),
            recommended=True,
            reason="Shortest unique attribute XPath for this element",
            framework_hint="AppiumBy.XPATH",
        )

    def _filter_redundant_composites(
        self, candidates: List[LocatorCandidate], tree: ElementNode
    ) -> List[LocatorCandidate]:
        """Drop UiSelector combos that don't improve uniqueness over simpler parts."""
        by_value: Dict[str, LocatorCandidate] = {}
        for loc in candidates:
            if loc.locator_type.value not in ("uiautomator2", "ui_automator", "composite"):
                by_value[loc.value] = loc
                continue
            mc = self._matcher.count_matches(tree, loc.locator_type.value, loc.value)
            simpler_better = False
            for other in candidates:
                if other.value == loc.value or len(other.value) >= len(loc.value):
                    continue
                if other.locator_type.value not in ("uiautomator2", "ui_automator", "composite"):
                    continue
                if loc.value.startswith(other.value.replace("d(", "d(")) or other.value in loc.value:
                    omc = self._matcher.count_matches(tree, other.locator_type.value, other.value)
                    if omc <= mc and omc > 0:
                        simpler_better = True
                        break
            if not simpler_better:
                by_value[loc.value] = loc
        return list(by_value.values())

    def _enrich(
        self,
        loc: LocatorCandidate,
        tree: ElementNode,
        element: ElementNode,
        analysis: ElementAnalysisContext,
    ) -> None:
        mc = self._matcher.count_matches(tree, loc.locator_type.value, loc.value)
        loc.match_count = mc
        loc.valid = mc > 0
        loc.is_duplicate = mc > 1
        loc.scores = self._adjust_uniqueness(loc.scores, mc)
        loc.category = self._categorize(loc).value
        loc.layout_dependency = self._layout_dependency(loc, analysis)
        loc.badge = self._badge_for(loc).value
        loc.star_rating = self._star_rating(loc)
        loc.performance_rating = loc.performance_rating or self._performance_rating(loc)
        loc.robustness = loc.robustness or self._robustness(loc, mc)
        if not loc.export_formats:
            loc.export_formats = self._default_exports(loc, element)

    def _categorize(self, loc: LocatorCandidate) -> LocatorCategory:
        name = loc.display_name.lower()
        t = loc.locator_type.value
        if t == "coordinate":
            return LocatorCategory.COORDINATE
        if t == "composite" or "+" in name:
            return LocatorCategory.COMBINED
        if t == "xpath_relative" or "child of" in name or "descendant of" in name or "sibling" in name.lower():
            return LocatorCategory.RELATIVE
        if "shortest unique" in name or t in ("xpath_contains", "xpath_starts_with", "xpath_ends_with", "xpath_axis"):
            return LocatorCategory.ADVANCED_XPATH
        if t == "xpath" or "xpath" in name:
            return LocatorCategory.XPATH
        if t == "ui_automator" or "uiselector" in name:
            return LocatorCategory.UISELECTOR
        if t in ("resource_id", "id"):
            return LocatorCategory.RESOURCE_ID
        if t in ("accessibility_id", "content_desc"):
            return LocatorCategory.ACCESSIBILITY
        if t == "text":
            return LocatorCategory.TEXT
        if t == "class_name":
            return LocatorCategory.CLASS_NAME
        if "package" in name:
            return LocatorCategory.PACKAGE
        if t == "instance" or "index" in name:
            return LocatorCategory.INDEX
        if t == "uiautomator2":
            if "resourceid" in name.replace("-", "").replace(" ", ""):
                return LocatorCategory.RESOURCE_ID
            if "description" in name:
                return LocatorCategory.ACCESSIBILITY
            if "text" in name:
                return LocatorCategory.TEXT
            if "class" in name:
                return LocatorCategory.CLASS_NAME
            if "package" in name:
                return LocatorCategory.PACKAGE
            if "index" in name or "instance" in name:
                return LocatorCategory.INDEX
            return LocatorCategory.UISELECTOR
        return LocatorCategory.OTHER

    @staticmethod
    def _badge_for(loc: LocatorCandidate) -> LocatorBadge:
        if loc.match_count != 1:
            return LocatorBadge.AVOID
        if loc.recommended and loc.scores.overall >= 0.75:
            return LocatorBadge.RECOMMENDED
        if loc.scores.overall >= 0.70:
            return LocatorBadge.GOOD
        if loc.scores.overall >= 0.50:
            return LocatorBadge.FAIR
        return LocatorBadge.AVOID

    @staticmethod
    def _star_rating(loc: LocatorCandidate) -> float:
        base = loc.scores.overall * 5
        if loc.match_count != 1:
            base = min(base, 2.0)
        if "index" in loc.display_name.lower() or loc.locator_type.value == "instance":
            base = min(base, 2.5)
        return round(max(0.5, min(5.0, base)), 1)

    @staticmethod
    def _layout_dependency(loc: LocatorCandidate, analysis: ElementAnalysisContext) -> float:
        dep = 0.3
        if loc.locator_type.value in ("xpath_relative",) or "relative" in (loc.category or ""):
            dep = 0.55
        if "absolute" in loc.display_name.lower():
            dep = 0.95
        if loc.locator_type.value in ("instance",) or "index" in loc.display_name.lower():
            dep = 0.85
        if analysis.is_in_recyclerview:
            dep = min(1.0, dep + 0.15)
        return round(dep, 2)

    def _group_locators(self, locators: List[LocatorCandidate]) -> List[LocatorGroup]:
        buckets: Dict[str, List[LocatorCandidate]] = {k: [] for k in _CATEGORY_ORDER}
        for loc in locators:
            cat = loc.category or LocatorCategory.OTHER.value
            if cat not in buckets:
                cat = LocatorCategory.OTHER.value
            buckets[cat].append(loc)
        return [
            LocatorGroup(category=cat, label=_CATEGORY_LABELS.get(cat, cat), locators=buckets[cat])
            for cat in _CATEGORY_ORDER
            if buckets[cat]
        ]

    def _apply_recommendations(self, candidates: List[LocatorCandidate]) -> None:
        unstable_patterns = (r"/\d+$", r"uuid", r"instance=\d+", r"index=\d+", r"absolute")
        for c in candidates:
            c.recommended = False
            val_lower = c.value.lower()
            name_lower = c.display_name.lower()
            if c.match_count != 1:
                continue
            if c.locator_type.value in ("coordinate", "bounds"):
                continue
            if "absolute" in name_lower or (c.locator_type.value == "xpath" and c.scores.stability <= 0.35):
                continue
            if any(re.search(p, val_lower + name_lower) for p in unstable_patterns):
                continue
            if c.scores.overall >= 0.65 and c.robustness in ("high", "medium"):
                c.recommended = True

        if candidates:
            top = max((c.scores.overall for c in candidates if c.recommended), default=0)
            for c in candidates:
                if c.recommended and c.scores.overall < top - 0.08:
                    c.recommended = False

        if candidates and not any(c.recommended for c in candidates):
            candidates[0].recommended = True

    @staticmethod
    def _adjust_uniqueness(scores: LocatorScore, match_count: int) -> LocatorScore:
        if match_count <= 0:
            match_count = 1
        uniqueness = 1.0 if match_count == 1 else max(0.1, 1.0 / match_count)
        stability = scores.stability
        if match_count > 3:
            stability = max(0.2, stability - 0.15)
        return LocatorRanker.base_scores(stability, uniqueness, scores.maintainability)

    @staticmethod
    def _performance_rating(loc: LocatorCandidate) -> str:
        t = loc.locator_type.value
        if t in ("resource_id", "accessibility_id", "content_desc", "uiautomator2"):
            if "Contains" not in loc.value and "Matches" not in loc.value:
                return "fast"
        if t.startswith("xpath") and "descendant" not in loc.value:
            return "medium"
        if "regex" in loc.display_name.lower() or "Matches" in loc.value:
            return "slow"
        return "medium"

    @staticmethod
    def _robustness(loc: LocatorCandidate, match_count: int) -> str:
        if match_count != 1:
            return "low"
        if loc.locator_type.value in ("coordinate", "bounds", "instance") or "index" in loc.display_name.lower():
            return "low"
        if "absolute" in loc.display_name.lower():
            return "low"
        if loc.scores.overall >= 0.80:
            return "high"
        if loc.scores.overall >= 0.60:
            return "medium"
        return "low"

    def _default_exports(self, loc: LocatorCandidate, element: ElementNode) -> Dict[str, str]:
        exports: Dict[str, str] = {}
        t = loc.locator_type.value
        if t in ("uiautomator2", "composite", "instance"):
            exports["uiautomator2"] = loc.value
        elif t == "ui_automator":
            exports["ui_automator"] = loc.value
            exports["appium"] = loc.value
        elif t == "resource_id":
            short = loc.value.split("/")[-1] if "/" in loc.value else loc.value
            exports["appium"] = f"id={short}"
            exports["uiautomator2"] = f'd(resourceId="{loc.value}")'
        elif t == "text":
            exports["appium"] = f'-android uiautomator:new UiSelector().text("{loc.value}")'
            exports["uiautomator2"] = f'd(text="{loc.value}")'
        elif t in ("content_desc", "accessibility_id"):
            exports["appium"] = f'accessibility id={loc.value}'
            exports["uiautomator2"] = f'd(description="{loc.value}")'
        elif t.startswith("xpath"):
            exports["xpath"] = loc.value
            exports["appium"] = loc.value
        return exports

    def _cache_key(self, element: ElementNode, tree: ElementNode) -> str:
        tree_sig = self._tree_signature(tree)
        el_sig = element.stable_key or element.id or str(element.bounds)
        return f"{tree_sig}:{el_sig}"

    def _tree_signature(self, tree: ElementNode) -> str:
        parts: List[str] = []

        def walk(n: ElementNode) -> None:
            parts.append(f"{n.id}|{n.resource_id}|{n.text}|{n.class_name}")
            for c in n.children:
                walk(c)

        walk(tree)
        return hashlib.sha256("\n".join(parts[:5000]).encode()).hexdigest()[:16]

    def _store_cache(self, key: str, bundle: LocatorBundle) -> None:
        if len(self._cache) >= self.CACHE_MAX:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = bundle

    @staticmethod
    def _is_dynamic_text(text: str) -> bool:
        return len(text) > 40 or bool(_VOLATILE_TEXT.search(text))

    @staticmethod
    def _esc(value: str) -> str:
        return value.replace("'", "\\'").replace('"', '\\"')
