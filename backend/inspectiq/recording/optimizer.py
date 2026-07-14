"""Script optimization — dedupe waits, merge scrolls, prefer stable locators."""

from __future__ import annotations

from inspectiq.domain.models import LocatorType
from inspectiq.recording.models import RecordedActionType, RecordedStep, RecordingSession


class RecordingOptimizer:
    """Post-process recorded steps before final script assembly."""

    def optimize(self, session: RecordingSession) -> RecordingSession:
        steps = list(session.steps)
        steps = self._remove_duplicate_waits(steps)
        steps = self._merge_consecutive_scrolls(steps)
        steps = self._prefer_stable_locators(steps)
        steps = self._flag_duplicate_taps(steps)
        session.steps = steps
        return session

    @staticmethod
    def _flag_duplicate_taps(steps: list[RecordedStep]) -> list[RecordedStep]:
        seen: set[str] = set()
        for step in steps:
            if step.action_type != RecordedActionType.TAP or not step.locator:
                continue
            key = f"{step.locator.locator_type}:{step.locator.value}"
            if key in seen:
                step.needs_review = True
                step.review_reason = step.review_reason or "Duplicate tap on same element"
            seen.add(key)
        return steps

    @staticmethod
    def _remove_duplicate_waits(steps: list[RecordedStep]) -> list[RecordedStep]:
        seen_waits: set[str] = set()
        out: list[RecordedStep] = []
        for step in steps:
            if step.action_type in (
                RecordedActionType.WAIT,
                RecordedActionType.WAIT_VISIBLE,
                RecordedActionType.WAIT_CLICKABLE,
            ):
                if step.locator:
                    key = f"{step.locator.locator_type}:{step.locator.value}"
                elif step.code_snippet:
                    key = step.code_snippet
                else:
                    key = step.id
                if key in seen_waits:
                    continue
                seen_waits.add(key)
            out.append(step)
        return out

    @staticmethod
    def _merge_consecutive_scrolls(steps: list[RecordedStep]) -> list[RecordedStep]:
        if len(steps) < 2:
            return steps
        merged: list[RecordedStep] = []
        i = 0
        while i < len(steps):
            step = steps[i]
            if step.action_type == RecordedActionType.SCROLL:
                j = i + 1
                while j < len(steps) and steps[j].action_type == RecordedActionType.SCROLL:
                    j += 1
                if j > i + 1:
                    merged.append(step)
                    i = j
                    continue
            merged.append(step)
            i += 1
        return merged

    @staticmethod
    def _prefer_stable_locators(steps: list[RecordedStep]) -> list[RecordedStep]:
        fragile = {LocatorType.XPATH, LocatorType.COORDINATE, LocatorType.BOUNDS}
        for step in steps:
            if not step.locator or step.locator.locator_type not in fragile:
                continue
            for alt in step.alternative_locators:
                if alt.locator_type not in fragile and alt.scores.overall >= 0.65:
                    step.locator = alt
                    step.confidence = alt.scores.overall
                    break
        return steps
