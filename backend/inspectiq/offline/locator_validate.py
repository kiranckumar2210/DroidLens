"""Offline locator validation against UIAutomator XML — for CI and locator suites."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from inspectiq.engine.xml_parser import AndroidXmlParser
from inspectiq.locator.raw_validator import RawLocatorValidator


@dataclass
class LocatorCheckResult:
    screen: str
    element_name: str
    locator_type: str
    value: str
    valid: bool
    match_count: int
    unique: bool
    warning: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "screen": self.screen,
            "element_name": self.element_name,
            "locator_type": self.locator_type,
            "value": self.value,
            "valid": self.valid,
            "match_count": self.match_count,
            "unique": self.unique,
            "warning": self.warning,
            "error": self.error,
        }


@dataclass
class LocatorValidationReport:
    passed: int
    failed: int
    total: int
    results: List[LocatorCheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failed == 0 and self.total > 0

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "total": self.total,
            "ok": self.ok,
            "results": [r.to_dict() for r in self.results],
        }


def _load_suite(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "screens" not in data and "elements" in data:
        return {"screens": [{"name": data.get("screen_name", "Screen"), "elements": data["elements"]}]}
    return data


def validate_locators_against_xml(
    raw_xml: str,
    locators_data: dict | list,
    *,
    screen_name: str = "Screen",
    require_unique: bool = True,
) -> LocatorValidationReport:
    parser = AndroidXmlParser()
    tree, _ = parser.parse(raw_xml)
    validator = RawLocatorValidator()
    results: List[LocatorCheckResult] = []

    elements: list[dict] = []
    if isinstance(locators_data, list):
        elements = locators_data
    elif isinstance(locators_data, dict):
        if "elements" in locators_data:
            elements = locators_data["elements"]
        elif "screens" in locators_data:
            for screen in locators_data["screens"]:
                for el in screen.get("elements") or []:
                    elements.append({**el, "_screen": screen.get("name", screen_name)})
        else:
            elements = []

    for el in elements:
        loc_type = el.get("locator_type") or el.get("type") or "xpath"
        value = el.get("value") or el.get("locator_value") or ""
        name = el.get("name") or el.get("element_name") or "element"
        screen = el.get("_screen") or el.get("screen") or screen_name
        if not value.strip():
            results.append(LocatorCheckResult(
                screen=screen, element_name=name, locator_type=loc_type, value=value,
                valid=False, match_count=0, unique=False, error="Empty locator value",
            ))
            continue
        r = validator.validate(tree, loc_type, value)
        unique = bool(r.get("unique"))
        valid = bool(r.get("valid")) and (not require_unique or unique)
        results.append(LocatorCheckResult(
            screen=screen,
            element_name=name,
            locator_type=loc_type,
            value=value,
            valid=valid,
            match_count=int(r.get("match_count") or 0),
            unique=unique,
            warning=r.get("warning"),
            error=r.get("error"),
        ))

    passed = sum(1 for r in results if r.valid)
    failed = len(results) - passed
    return LocatorValidationReport(passed=passed, failed=failed, total=len(results), results=results)


def validate_locator_suite_file(
    xml_path: Path,
    suite_path: Path,
    *,
    require_unique: bool = True,
) -> LocatorValidationReport:
    suite = _load_suite(suite_path)
    screen_name = xml_path.stem
    if isinstance(suite, dict) and suite.get("screens"):
        for screen in suite["screens"]:
            xml_file = screen.get("xml_file")
            if xml_file and Path(xml_file).stem != screen_name and xml_file != xml_path.name:
                continue
            if screen.get("elements"):
                return validate_locators_against_xml(
                    xml_path.read_text(encoding="utf-8"),
                    screen,
                    screen_name=screen.get("name", screen_name),
                    require_unique=require_unique,
                )
    return validate_locators_against_xml(
        xml_path.read_text(encoding="utf-8"),
        suite,
        screen_name=screen_name,
        require_unique=require_unique,
    )


def validate_folder(
    folder: Path,
    suite_path: Path,
    *,
    require_unique: bool = True,
) -> LocatorValidationReport:
    suite = _load_suite(suite_path)
    all_results: List[LocatorCheckResult] = []
    screens = suite.get("screens") if isinstance(suite, dict) else []

    if screens:
        for screen in screens:
            xml_name = screen.get("xml_file") or f"{screen.get('name', 'Screen')}.xml"
            xml_path = folder / xml_name
            if not xml_path.is_file():
                all_results.append(LocatorCheckResult(
                    screen=screen.get("name", xml_name),
                    element_name="(file)",
                    locator_type="",
                    value="",
                    valid=False,
                    match_count=0,
                    unique=False,
                    error=f"Missing XML: {xml_name}",
                ))
                continue
            report = validate_locators_against_xml(
                xml_path.read_text(encoding="utf-8"),
                screen,
                screen_name=screen.get("name", xml_path.stem),
                require_unique=require_unique,
            )
            all_results.extend(report.results)
    else:
        for xml_path in sorted(folder.glob("*.xml")):
            report = validate_locator_suite_file(xml_path, suite_path, require_unique=require_unique)
            all_results.extend(report.results)

    passed = sum(1 for r in all_results if r.valid)
    failed = len(all_results) - passed
    return LocatorValidationReport(passed=passed, failed=failed, total=len(all_results), results=all_results)
