"""Suggest replacement locators when UI hierarchy changes between builds."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from inspectiq.domain.models import ElementNode, LocatorCandidate
from inspectiq.engine.element_selector import SmartElementSelector
from inspectiq.engine.xml_parser import AndroidXmlParser
from inspectiq.locator.engine import LocatorEngine
from inspectiq.locator.raw_validator import RawLocatorValidator


@dataclass
class MigrationSuggestion:
    reason: str
    element_id: str
    resource_id: Optional[str]
    class_name: str
    locators: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "reason": self.reason,
            "element_id": self.element_id,
            "resource_id": self.resource_id,
            "class_name": self.class_name,
            "locators": self.locators,
        }


@dataclass
class LocatorMigrationResult:
    broken_locator_type: str
    broken_locator_value: str
    old_match_count: int
    new_match_count: int
    status: str
    message: str
    suggestions: List[MigrationSuggestion] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "broken_locator_type": self.broken_locator_type,
            "broken_locator_value": self.broken_locator_value,
            "old_match_count": self.old_match_count,
            "new_match_count": self.new_match_count,
            "status": self.status,
            "message": self.message,
            "suggestions": [s.to_dict() for s in self.suggestions],
        }


def _find_corresponding(old_node: ElementNode, new_tree: ElementNode) -> Optional[ElementNode]:
    flat = SmartElementSelector().flatten(new_tree)
    if old_node.resource_id:
        for n in flat:
            if n.resource_id == old_node.resource_id:
                return n
    if old_node.content_desc:
        for n in flat:
            if n.content_desc == old_node.content_desc:
                return n
    if old_node.text:
        for n in flat:
            if n.text == old_node.text and n.class_name == old_node.class_name:
                return n
    if old_node.class_name and old_node.bounds:
        ob = old_node.bounds
        for n in flat:
            if n.class_name != old_node.class_name or not n.bounds:
                continue
            nb = n.bounds
            if abs(ob.x1 - nb.x1) < 8 and abs(ob.y1 - nb.y1) < 8:
                return n
    return None


def _locator_to_dict(loc: LocatorCandidate) -> dict:
    return {
        "locator_type": loc.locator_type.value if hasattr(loc.locator_type, "value") else str(loc.locator_type),
        "value": loc.value,
        "display_name": loc.display_name,
        "recommended": loc.recommended,
        "overall_score": loc.scores.overall,
        "reason": loc.reason,
    }


def migrate_locator(
    old_xml: str,
    new_xml: str,
    locator_type: str,
    locator_value: str,
    *,
    max_suggestions: int = 5,
) -> LocatorMigrationResult:
    parser = AndroidXmlParser()
    old_tree, _ = parser.parse(old_xml)
    new_tree, _ = parser.parse(new_xml)
    validator = RawLocatorValidator()
    engine = LocatorEngine()

    old_result = validator.validate(old_tree, locator_type, locator_value)
    new_result = validator.validate(new_tree, locator_type, locator_value)
    old_count = int(old_result.get("match_count") or 0)
    new_count = int(new_result.get("match_count") or 0)

    if new_count == 1:
        return LocatorMigrationResult(
            broken_locator_type=locator_type,
            broken_locator_value=locator_value,
            old_match_count=old_count,
            new_match_count=new_count,
            status="ok",
            message="Locator still matches uniquely in the new hierarchy — no migration needed.",
        )

    if old_count == 0:
        return LocatorMigrationResult(
            broken_locator_type=locator_type,
            broken_locator_value=locator_value,
            old_match_count=0,
            new_match_count=new_count,
            status="error",
            message="Locator did not match the baseline XML either — verify the baseline dump.",
        )

    old_nodes: List[ElementNode] = []
    selector = SmartElementSelector()
    for eid in old_result.get("matched_ids") or []:
        node = selector.find_by_id(old_tree, str(eid))
        if node:
            old_nodes.append(node)
    if not old_nodes and old_result.get("matched_elements"):
        for item in old_result["matched_elements"]:
            if isinstance(item, ElementNode):
                old_nodes.append(item)

    suggestions: List[MigrationSuggestion] = []

    for old_node in old_nodes[:max_suggestions]:
        new_node = _find_corresponding(old_node, new_tree)
        if not new_node:
            continue
        bundle = engine.generate_bundle(new_node, new_tree)
        top = bundle.all_locators[:5]
        suggestions.append(MigrationSuggestion(
            reason=f"Mapped from old element ({old_node.resource_id or old_node.class_name})",
            element_id=new_node.id,
            resource_id=new_node.resource_id,
            class_name=new_node.class_name,
            locators=[_locator_to_dict(loc) for loc in top],
        ))

    if not suggestions:
        return LocatorMigrationResult(
            broken_locator_type=locator_type,
            broken_locator_value=locator_value,
            old_match_count=old_count,
            new_match_count=new_count,
            status="not_found",
            message="Could not map old matched elements to the new hierarchy — UI may have changed significantly.",
        )

    status = "ambiguous" if new_count > 1 else "broken"
    msg = (
        f"Locator matches {new_count} element(s) in new XML (was {old_count} in old). "
        f"{len(suggestions)} replacement candidate(s) found."
    )
    return LocatorMigrationResult(
        broken_locator_type=locator_type,
        broken_locator_value=locator_value,
        old_match_count=old_count,
        new_match_count=new_count,
        status=status,
        message=msg,
        suggestions=suggestions,
    )
