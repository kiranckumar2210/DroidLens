#!/usr/bin/env python3
"""DroidLens CLI — offline validation for CI pipelines."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from inspectiq.offline.locator_health import scan_xml_health
from inspectiq.offline.locator_validate import (
    validate_folder,
    validate_locator_suite_file,
    validate_locators_against_xml,
)


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_validate_locators(args: argparse.Namespace) -> int:
    xml_path = Path(args.xml)
    suite_path = Path(args.locators)
    if not xml_path.is_file():
        print(f"ERROR: XML not found: {xml_path}", file=sys.stderr)
        return 2
    if not suite_path.is_file():
        print(f"ERROR: Locators file not found: {suite_path}", file=sys.stderr)
        return 2
    report = validate_locator_suite_file(
        xml_path, suite_path, require_unique=not args.allow_ambiguous,
    )
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"Validated {report.total} locator(s): {report.passed} passed, {report.failed} failed")
        for r in report.results:
            mark = "OK" if r.valid else "FAIL"
            print(f"  [{mark}] {r.screen}/{r.element_name}: {r.locator_type} → {r.match_count} match(es)")
            if r.error:
                print(f"         {r.error}")
            elif r.warning:
                print(f"         {r.warning}")
    return 0 if report.ok else 1


def cmd_validate_folder(args: argparse.Namespace) -> int:
    folder = Path(args.dir)
    suite_path = Path(args.locators)
    if not folder.is_dir():
        print(f"ERROR: Folder not found: {folder}", file=sys.stderr)
        return 2
    report = validate_folder(folder, suite_path, require_unique=not args.allow_ambiguous)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"Folder {folder}: {report.passed}/{report.total} passed")
        for r in report.results:
            if not r.valid:
                print(f"  FAIL {r.screen}/{r.element_name}: {r.error or r.warning or r.value[:60]}")
    return 0 if report.ok else 1


def cmd_health_scan(args: argparse.Namespace) -> int:
    xml_path = Path(args.xml)
    if not xml_path.is_file():
        print(f"ERROR: XML not found: {xml_path}", file=sys.stderr)
        return 2
    report = scan_xml_health(xml_path.read_text(encoding="utf-8"), xml_path.stem)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"{report.screen_name}: score {report.score}/100, {report.issue_count} issue(s)")
        for issue in report.issues[:20]:
            print(f"  [{issue.severity}] {issue.code}: {issue.message}")
    min_score = args.min_score
    if report.score < min_score:
        print(f"FAIL: score {report.score} below minimum {min_score}", file=sys.stderr)
        return 1
    return 0


def cmd_validate_inline(args: argparse.Namespace) -> int:
    xml_path = Path(args.xml)
    locators = _load_json(Path(args.locators))
    report = validate_locators_against_xml(
        xml_path.read_text(encoding="utf-8"),
        locators,
        screen_name=xml_path.stem,
        require_unique=not args.allow_ambiguous,
    )
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="droidlens",
        description="DroidLens offline tools for CI — validate locators against UIAutomator XML dumps.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_val = sub.add_parser("validate-locators", help="Validate locators JSON against one XML file")
    p_val.add_argument("--xml", required=True, help="Path to UIAutomator XML dump")
    p_val.add_argument("--locators", required=True, help="Path to locator suite JSON")
    p_val.add_argument("--allow-ambiguous", action="store_true", help="Allow locators with multiple matches")
    p_val.add_argument("--json", action="store_true", help="Output JSON report")
    p_val.set_defaults(func=cmd_validate_locators)

    p_folder = sub.add_parser("validate-folder", help="Validate locator suite against a folder of XML files")
    p_folder.add_argument("--dir", required=True, help="Folder containing XML dumps")
    p_folder.add_argument("--locators", required=True, help="Path to locator suite JSON")
    p_folder.add_argument("--allow-ambiguous", action="store_true")
    p_folder.add_argument("--json", action="store_true")
    p_folder.set_defaults(func=cmd_validate_folder)

    p_health = sub.add_parser("health-scan", help="Run locator health heuristics on an XML file")
    p_health.add_argument("--xml", required=True)
    p_health.add_argument("--min-score", type=int, default=0, help="Exit 1 if score below this")
    p_health.add_argument("--json", action="store_true")
    p_health.set_defaults(func=cmd_health_scan)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
