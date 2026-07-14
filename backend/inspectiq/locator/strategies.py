"""Locator generation strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod

from inspectiq.domain.models import ElementNode, LocatorCandidate, LocatorType, Platform


class LocatorStrategy(ABC):
    @abstractmethod
    def supports(self, platform: Platform) -> bool:
        ...

    @abstractmethod
    def generate(self, element: ElementNode) -> list[LocatorCandidate]:
        ...


class AccessibilityStrategy(LocatorStrategy):
    def supports(self, platform: Platform) -> bool:
        return True

    def generate(self, element: ElementNode) -> list[LocatorCandidate]:
        results = []
        aid = element.accessibility_id or element.content_desc or element.name
        if aid:
            from inspectiq.locator.ranker import LocatorRanker

            candidate = LocatorCandidate(
                locator_type=LocatorType.ACCESSIBILITY_ID,
                value=aid,
                display_name="Accessibility ID",
                scores=LocatorRanker.base_scores(stability=0.95, uniqueness=1.0, maintainability=0.92),
                recommended=True,
                reason="Stable identifier, platform-supported, resists hierarchy changes",
                framework_hint="AppiumBy.ACCESSIBILITY_ID",
            )
            results.append(candidate)
        return results


class ResourceIdStrategy(LocatorStrategy):
    def supports(self, platform: Platform) -> bool:
        return platform in (Platform.ANDROID, Platform.HARMONYOS)

    def generate(self, element: ElementNode) -> list[LocatorCandidate]:
        if not element.resource_id:
            return []
        from inspectiq.locator.ranker import LocatorRanker

        return [
            LocatorCandidate(
                locator_type=LocatorType.RESOURCE_ID,
                value=element.resource_id,
                display_name="Resource ID",
                scores=LocatorRanker.base_scores(stability=0.90, uniqueness=0.95, maintainability=0.88),
                recommended=True,
                reason="Stable Android/HarmonyOS resource identifier",
                framework_hint="AppiumBy.ID",
            )
        ]


class UiAutomatorStrategy(LocatorStrategy):
    def supports(self, platform: Platform) -> bool:
        return platform == Platform.ANDROID

    def generate(self, element: ElementNode) -> list[LocatorCandidate]:
        from inspectiq.locator.ranker import LocatorRanker

        results = []
        parts = ["new UiSelector()"]
        if element.resource_id:
            rid = element.resource_id.split("/")[-1] if "/" in element.resource_id else element.resource_id
            parts.append(f'.resourceId("{element.resource_id}")')
        elif element.text:
            parts.append(f'.text("{element.text}")')
        elif element.content_desc:
            parts.append(f'.description("{element.content_desc}")')
        elif element.class_name:
            parts.append(f'.className("{element.class_name}")')
        else:
            return []

        value = "".join(parts)
        results.append(
            LocatorCandidate(
                locator_type=LocatorType.UI_AUTOMATOR,
                value=value,
                display_name="Android UiAutomator",
                scores=LocatorRanker.base_scores(stability=0.85, uniqueness=0.85, maintainability=0.80),
                recommended=True,
                reason="Native Android selector, expressive and readable",
                framework_hint="AppiumBy.ANDROID_UIAUTOMATOR",
            )
        )
        return results


class XPathStrategy(LocatorStrategy):
    def supports(self, platform: Platform) -> bool:
        return True

    def generate(self, element: ElementNode) -> list[LocatorCandidate]:
        from inspectiq.locator.ranker import LocatorRanker
        from inspectiq.locator.xpath_builder import XPathBuilder

        builder = XPathBuilder()
        examples = builder.build_all(element)
        results = []

        for ex in examples:
            if ex.axis == "absolute":
                score = LocatorRanker.base_scores(0.30, 0.90, 0.25)
                recommended = False
                reason = "Breaks when UI hierarchy changes — avoid for maintenance"
            elif ex.axis in ("contains", "starts-with"):
                score = LocatorRanker.base_scores(0.70, 0.75, 0.65)
                recommended = ex.axis == "contains"
                reason = "Partial match — useful when text is dynamic"
            elif ex.axis == "exact":
                score = LocatorRanker.base_scores(0.72, 0.88, 0.60)
                recommended = True
                reason = "Attribute-based XPath — acceptable when IDs unavailable"
            else:
                score = LocatorRanker.base_scores(0.55, 0.70, 0.50)
                recommended = False
                reason = f"Axis-based XPath ({ex.axis}) — use for navigation, not primary locator"

            loc_type = LocatorType.XPATH
            if ex.axis == "contains":
                loc_type = LocatorType.XPATH_CONTAINS
            elif ex.axis == "starts-with":
                loc_type = LocatorType.XPATH_STARTS_WITH
            elif ex.axis not in ("exact", "absolute"):
                loc_type = LocatorType.XPATH_AXIS

            results.append(
                LocatorCandidate(
                    locator_type=loc_type,
                    value=ex.xpath,
                    display_name=f"XPath ({ex.axis})",
                    scores=score,
                    recommended=recommended,
                    reason=reason,
                    framework_hint="AppiumBy.XPATH",
                )
            )
        return results


class IOSPredicateStrategy(LocatorStrategy):
    def supports(self, platform: Platform) -> bool:
        return platform == Platform.IOS

    def generate(self, element: ElementNode) -> list[LocatorCandidate]:
        from inspectiq.locator.ranker import LocatorRanker

        results = []
        if element.name:
            results.append(
                LocatorCandidate(
                    locator_type=LocatorType.IOS_PREDICATE,
                    value=f'name == "{element.name}"',
                    display_name="iOS Predicate (name)",
                    scores=LocatorRanker.base_scores(0.93, 0.95, 0.90),
                    recommended=True,
                    reason="Accessibility identifier — preferred for iOS",
                    framework_hint="AppiumBy.IOS_PREDICATE",
                )
            )
        if element.label:
            results.append(
                LocatorCandidate(
                    locator_type=LocatorType.IOS_PREDICATE,
                    value=f'label == "{element.label}"',
                    display_name="iOS Predicate (label)",
                    scores=LocatorRanker.base_scores(0.80, 0.80, 0.75),
                    recommended=not element.name,
                    reason="Label-based predicate — may change with localization",
                    framework_hint="AppiumBy.IOS_PREDICATE",
                )
            )
        return results


class IOSClassChainStrategy(LocatorStrategy):
    def supports(self, platform: Platform) -> bool:
        return platform == Platform.IOS

    def generate(self, element: ElementNode) -> list[LocatorCandidate]:
        if not element.type_name and not element.class_name:
            return []
        from inspectiq.locator.ranker import LocatorRanker

        type_name = element.type_name or element.class_name
        chain = f"**/{type_name}"
        if element.name:
            chain += f"[`name == \"{element.name}\"`]"
        elif element.label:
            chain += f"[`label == \"{element.label}\"`]"

        return [
            LocatorCandidate(
                locator_type=LocatorType.IOS_CLASS_CHAIN,
                value=chain,
                display_name="iOS Class Chain",
                scores=LocatorRanker.base_scores(0.88, 0.90, 0.85),
                recommended=True,
                reason="Fast iOS-native locator strategy",
                framework_hint="AppiumBy.IOS_CLASS_CHAIN",
            )
        ]


class CoordinateStrategy(LocatorStrategy):
    def supports(self, platform: Platform) -> bool:
        return True

    def generate(self, element: ElementNode) -> list[LocatorCandidate]:
        if not element.bounds:
            return []
        from inspectiq.locator.ranker import LocatorRanker

        x, y = element.bounds.center_x, element.bounds.center_y
        has_stable = bool(
            element.accessibility_id or element.resource_id or element.name or element.content_desc
        )
        stability = 0.45 if not has_stable else 0.35
        reason = (
            "Element has no accessibility identifier and no stable attribute — coordinate tap suggested"
            if not has_stable
            else "Coordinate fallback — use only when semantic locators fail (canvas, custom views, games)"
        )

        return [
            LocatorCandidate(
                locator_type=LocatorType.COORDINATE,
                value=f"x={x}, y={y}",
                display_name="Tap Coordinates",
                scores=LocatorRanker.base_scores(stability, 1.0, 0.20),
                recommended=not has_stable,
                reason=reason,
                framework_hint="TouchAction / mobile: tap",
            )
        ]


ALL_STRATEGIES: list[LocatorStrategy] = [
    AccessibilityStrategy(),
    ResourceIdStrategy(),
    UiAutomatorStrategy(),
    IOSPredicateStrategy(),
    IOSClassChainStrategy(),
    XPathStrategy(),
    CoordinateStrategy(),
]
