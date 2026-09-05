"""Convert locator repository rows to CSV and Markdown."""

from __future__ import annotations

import csv
import io
import json
from typing import Any


def repository_to_json(rows: list[dict]) -> str:
    return json.dumps(
        {"format": "droidlens-locator-repository", "formatVersion": 1, "elements": rows},
        indent=2,
        ensure_ascii=False,
    )


def repository_to_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "project", "feature", "screen", "platform", "element_name", "class_name",
        "locator_type", "locator_value", "overall_score", "is_primary", "recommended", "reason",
    ])
    for row in rows:
        for loc in row.get("locators") or []:
            writer.writerow([
                row.get("project", ""),
                row.get("feature", ""),
                row.get("screen", ""),
                row.get("platform", ""),
                row.get("element_name", ""),
                row.get("class_name", ""),
                loc.get("locator_type", ""),
                loc.get("value", ""),
                f"{(loc.get('overall') or 0) * 100:.0f}%",
                "yes" if loc.get("is_primary") else "",
                "yes" if loc.get("recommended") else "",
                loc.get("reason", ""),
            ])
    return buf.getvalue()


def repository_to_markdown(rows: list[dict]) -> str:
    lines = [
        "# DroidLens Locator Repository",
        "",
        f"**Elements:** {len(rows)}",
        "",
        "## Summary",
        "",
        "| Project | Feature | Screen | Element | Primary Locator | Score |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        primary = row.get("primary_locator") or {}
        score = f"{(primary.get('overall') or 0) * 100:.0f}%" if primary else "—"
        loc_val = (primary.get("value") or "—").replace("|", "\\|")
        lines.append(
            f"| {row.get('project', '')} | {row.get('feature', '')} | {row.get('screen', '')} "
            f"| {row.get('element_name', '')} | `{loc_val[:80]}{'…' if len(loc_val) > 80 else ''}` | {score} |"
        )
    lines.extend(["", "## All Locators", ""])
    for row in rows:
        lines.append(f"### {row.get('element_name', 'element')} — {row.get('screen', '')}")
        lines.append("")
        for loc in row.get("locators") or []:
            tags = []
            if loc.get("is_primary"):
                tags.append("primary")
            if loc.get("recommended"):
                tags.append("recommended")
            tag_str = f" ({', '.join(tags)})" if tags else ""
            lines.append(f"- **{loc.get('locator_type', '')}**{tag_str}: `{loc.get('value', '')}`")
        lines.append("")
    return "\n".join(lines)


def format_repository(rows: list[dict], fmt: str) -> tuple[str, str, str]:
    """Return (content, media_type, filename_suffix)."""
    normalized = fmt.lower().strip()
    if normalized == "csv":
        return repository_to_csv(rows), "text/csv", "locators.csv"
    if normalized in ("md", "markdown"):
        return repository_to_markdown(rows), "text/markdown", "locators.md"
    return repository_to_json(rows), "application/json", "locators.json"
