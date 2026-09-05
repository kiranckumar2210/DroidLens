"""Heuristic locator health scan for offline XML dumps."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional

from inspectiq.domain.models import ElementNode
from inspectiq.engine.xml_parser import AndroidXmlParser


@dataclass
class LocatorHealthIssue:
    severity: str  # error | warn | info
    code: str
    message: str
    element_path: str
    class_name: str
    resource_id: Optional[str] = None
    hint: Optional[str] = None

    def to_dict(self) -> dict:
        return self.__dict__


@dataclass
class LocatorHealthReport:
    screen_name: str
    node_count: int
    clickable_count: int
    issues: List[LocatorHealthIssue] = field(default_factory=list)

    @property
    def score(self) -> int:
        """0–100 health score."""
        if not self.issues:
            return 100
        penalty = sum(10 if i.severity == "error" else 5 if i.severity == "warn" else 1 for i in self.issues)
        return max(0, 100 - min(penalty, 100))

    def to_dict(self) -> dict:
        return {
            "screen_name": self.screen_name,
            "node_count": self.node_count,
            "clickable_count": self.clickable_count,
            "score": self.score,
            "issue_count": len(self.issues),
            "issues": [i.to_dict() for i in self.issues[:500]],
        }


def scan_xml_health(raw_xml: str, screen_name: str = "Screen") -> LocatorHealthReport:
    parser = AndroidXmlParser()
    tree, _ = parser.parse(raw_xml)
    issues: List[LocatorHealthIssue] = []
    node_count = 0
    clickable_count = 0
    resource_ids: Counter[str] = Counter()

    def walk(node: ElementNode, path: str) -> None:
        nonlocal node_count, clickable_count
        node_count += 1
        if node.clickable or node.long_clickable:
            clickable_count += 1
            if not node.resource_id and not node.content_desc and not (node.text and node.text.strip()):
                issues.append(LocatorHealthIssue(
                    severity="error",
                    code="no_stable_id",
                    message="Clickable element lacks resource-id, content-desc, and text",
                    element_path=path,
                    class_name=node.class_name,
                    hint="Add accessibility labels or use relative XPath from a stable anchor",
                ))
        if node.resource_id:
            resource_ids[node.resource_id] += 1
        if node.depth > 18:
            issues.append(LocatorHealthIssue(
                severity="warn",
                code="deep_hierarchy",
                message=f"Element at depth {node.depth} — brittle XPath",
                element_path=path,
                class_name=node.class_name,
                resource_id=node.resource_id,
            ))
        if node.password:
            issues.append(LocatorHealthIssue(
                severity="info",
                code="password_field",
                message="Password field — prefer resource-id over text locators",
                element_path=path,
                class_name=node.class_name,
                resource_id=node.resource_id,
            ))
        for i, child in enumerate(node.children):
            walk(child, f"{path}/{i}")

    walk(tree, "0")

    for rid, count in resource_ids.items():
        if count > 1:
            issues.append(LocatorHealthIssue(
                severity="warn",
                code="duplicate_resource_id",
                message=f"resource-id appears {count} times: {rid}",
                element_path="",
                class_name="",
                resource_id=rid,
                hint="Use index or parent context in locators",
            ))

    return LocatorHealthReport(
        screen_name=screen_name,
        node_count=node_count,
        clickable_count=clickable_count,
        issues=issues,
    )
