"""Locator resolution for recorded interactions — wraps DroidLens locator engine."""

from __future__ import annotations

from typing import Literal, Optional

from inspectiq.domain.models import ElementInspectionResult, LocatorCandidate, LocatorType
from inspectiq.recording.interfaces import LocatorResolutionService
from inspectiq.services.inspection_service import InspectionService

STRATEGY_PRIORITY = {
    "resource_id": [LocatorType.RESOURCE_ID, LocatorType.ID],
    "content_desc": [LocatorType.CONTENT_DESC, LocatorType.ACCESSIBILITY_ID],
    "text": [LocatorType.TEXT],
    "uiautomator": [LocatorType.UIAUTOMATOR2, LocatorType.UI_AUTOMATOR],
    "xpath": [LocatorType.XPATH_RELATIVE, LocatorType.XPATH],
}

# Preferred locator types for recorded automation (stable + element-specific).
RECORDING_LOCATOR_PRIORITY = [
    LocatorType.RESOURCE_ID,
    LocatorType.ID,
    LocatorType.CONTENT_DESC,
    LocatorType.ACCESSIBILITY_ID,
    LocatorType.TEXT,
    LocatorType.UIAUTOMATOR2,
    LocatorType.UI_AUTOMATOR,
    LocatorType.COMPOSITE,
    LocatorType.XPATH_RELATIVE,
    LocatorType.XPATH,
]

FragileLocatorTypes = frozenset({
    LocatorType.COORDINATE,
    LocatorType.BOUNDS,
    LocatorType.INSTANCE,
})


class DefaultLocatorResolutionService(LocatorResolutionService):
    def __init__(self, inspection: InspectionService):
        self._inspection = inspection

    def resolve_at(
        self,
        device_id: str,
        x: int,
        y: int,
        *,
        coord_space: Literal["screenshot", "device"] = "screenshot",
    ) -> Optional[ElementInspectionResult]:
        try:
            return self._inspection.inspect_element_at(
                device_id, x, y, coord_space=coord_space
            )
        except Exception:
            return None

    def resolve_by_id(self, device_id: str, element_id: str) -> Optional[ElementInspectionResult]:
        try:
            return self._inspection.inspect_element_by_id(device_id, element_id)
        except Exception:
            return None

    def pick_best_locator(self, inspection: ElementInspectionResult, strategy: str = "auto") -> LocatorCandidate:
        locators = list(inspection.locators)
        if not locators and inspection.coordinate_fallback:
            return inspection.coordinate_fallback

        if strategy != "auto" and strategy in STRATEGY_PRIORITY:
            preferred = STRATEGY_PRIORITY[strategy]
            pool = self._ranked_pool(locators)
            for ptype in preferred:
                for loc in pool:
                    if loc.locator_type == ptype:
                        return loc

        picked = self._pick_from_pool(self._ranked_pool(locators))
        if picked:
            return picked
        if inspection.coordinate_fallback:
            return inspection.coordinate_fallback
        raise ValueError("No locator candidates available")

    def _ranked_pool(self, locators: list[LocatorCandidate]) -> list[LocatorCandidate]:
        unique = [l for l in locators if l.match_count == 1]
        pool = unique if unique else locators
        recommended = [l for l in pool if l.recommended]
        return recommended if recommended else pool

    def _pick_from_pool(self, pool: list[LocatorCandidate]) -> Optional[LocatorCandidate]:
        if not pool:
            return None
        for ptype in RECORDING_LOCATOR_PRIORITY:
            for loc in pool:
                if loc.locator_type == ptype and loc.locator_type not in FragileLocatorTypes:
                    return loc
        for loc in pool:
            if loc.locator_type not in FragileLocatorTypes:
                return loc
        return pool[0]

    def alternatives(self, inspection: ElementInspectionResult, limit: int = 5) -> list[LocatorCandidate]:
        pool = self._ranked_pool(inspection.locators)
        return pool[:limit]
