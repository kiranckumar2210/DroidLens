"""Recording locator resolution tests."""

from inspectiq.domain.models import ElementInspectionResult, ElementNode, LocatorCandidate, LocatorScore, LocatorType, Platform
from inspectiq.recording.locator_resolution import DefaultLocatorResolutionService


def _locator(ltype: LocatorType, value: str, *, match_count: int = 1, recommended: bool = True, overall: float = 0.9) -> LocatorCandidate:
    return LocatorCandidate(
        locator_type=ltype,
        value=value,
        display_name=value,
        scores=LocatorScore(stability=overall, uniqueness=overall, maintainability=overall, overall=overall),
        recommended=recommended,
        match_count=match_count,
        valid=True,
        reason="test",
    )


def test_pick_best_locator_prefers_resource_id_over_xpath():
    svc = DefaultLocatorResolutionService(inspection=None)  # type: ignore[arg-type]
    element = ElementNode(id="e1", platform=Platform.ANDROID, resource_id="com.app:id/login")
    inspection = ElementInspectionResult(
        element=element,
        locators=[
            _locator(LocatorType.XPATH, "//android.widget.FrameLayout", overall=0.7),
            _locator(LocatorType.RESOURCE_ID, "com.app:id/login", overall=0.85),
        ],
    )
    picked = svc.pick_best_locator(inspection)
    assert picked.locator_type == LocatorType.RESOURCE_ID


def test_pick_best_locator_skips_non_unique():
    svc = DefaultLocatorResolutionService(inspection=None)  # type: ignore[arg-type]
    element = ElementNode(id="e1", platform=Platform.ANDROID, text="Login")
    inspection = ElementInspectionResult(
        element=element,
        locators=[
            _locator(LocatorType.RESOURCE_ID, "com.app:id/container", match_count=3, recommended=False, overall=0.5),
            _locator(LocatorType.CONTENT_DESC, "Login button", match_count=1, overall=0.8),
        ],
    )
    picked = svc.pick_best_locator(inspection)
    assert picked.locator_type == LocatorType.CONTENT_DESC
