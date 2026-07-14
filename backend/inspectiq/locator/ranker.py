"""Locator scoring utilities and legacy intelligence engine facade."""

from __future__ import annotations

from typing import TYPE_CHECKING

from inspectiq.domain.models import ElementNode, LocatorCandidate, LocatorScore

if TYPE_CHECKING:
    from inspectiq.locator.engine import LocatorEngine


class LocatorRanker:
    STABILITY_WEIGHT = 0.40
    UNIQUENESS_WEIGHT = 0.35
    MAINTAINABILITY_WEIGHT = 0.25

    @staticmethod
    def base_scores(stability: float, uniqueness: float, maintainability: float) -> LocatorScore:
        overall = (
            stability * LocatorRanker.STABILITY_WEIGHT
            + uniqueness * LocatorRanker.UNIQUENESS_WEIGHT
            + maintainability * LocatorRanker.MAINTAINABILITY_WEIGHT
        )
        return LocatorScore(
            stability=round(stability, 2),
            uniqueness=round(uniqueness, 2),
            maintainability=round(maintainability, 2),
            overall=round(overall, 2),
        )


class LocatorIntelligenceEngine:
    """Backward-compatible facade over LocatorEngine."""

    MAX_CANDIDATES = 100

    def __init__(self) -> None:
        from inspectiq.locator.engine import LocatorEngine

        self._engine: LocatorEngine = LocatorEngine()

    def generate_all(self, element: ElementNode, tree: ElementNode) -> list[LocatorCandidate]:
        return self._engine.generate_all(element, tree)

    def generate_bundle(self, element: ElementNode, tree: ElementNode):
        return self._engine.generate_bundle(element, tree)

    def preview(self, tree: ElementNode, locator_type: str, value: str) -> dict:
        return self._engine.preview(tree, locator_type, value)

    def compare(self, tree: ElementNode, locator_a: LocatorCandidate, locator_b: LocatorCandidate):
        return self._engine.compare_locators(tree, locator_a, locator_b)
