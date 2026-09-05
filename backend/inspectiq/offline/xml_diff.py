"""Compare two UIAutomator XML dumps and report structural changes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from inspectiq.domain.models import ElementNode
from inspectiq.engine.xml_parser import AndroidXmlParser


@dataclass
class NodeSnapshot:
    path: str
    class_name: str
    resource_id: Optional[str]
    text: Optional[str]
    content_desc: Optional[str]
    bounds: Optional[str]
    clickable: bool

    def signature(self) -> str:
        return "|".join([
            self.class_name or "",
            self.resource_id or "",
            (self.text or "")[:80],
            (self.content_desc or "")[:80],
            self.bounds or "",
            "1" if self.clickable else "0",
        ])


@dataclass
class XmlDiffResult:
    baseline_node_count: int
    compare_node_count: int
    added: List[NodeSnapshot] = field(default_factory=list)
    removed: List[NodeSnapshot] = field(default_factory=list)
    changed: List[dict] = field(default_factory=list)
    unchanged_count: int = 0

    def to_dict(self) -> dict:
        return {
            "baseline_node_count": self.baseline_node_count,
            "compare_node_count": self.compare_node_count,
            "added_count": len(self.added),
            "removed_count": len(self.removed),
            "changed_count": len(self.changed),
            "unchanged_count": self.unchanged_count,
            "added": [s.__dict__ for s in self.added[:200]],
            "removed": [s.__dict__ for s in self.removed[:200]],
            "changed": self.changed[:200],
        }


def _flatten(root: ElementNode, prefix: str = "0") -> Dict[str, NodeSnapshot]:
    out: Dict[str, NodeSnapshot] = {}
    bounds = root.bounds.to_string() if root.bounds else None
    out[prefix] = NodeSnapshot(
        path=prefix,
        class_name=root.class_name,
        resource_id=root.resource_id,
        text=root.text,
        content_desc=root.content_desc,
        bounds=bounds,
        clickable=root.clickable,
    )
    for i, child in enumerate(root.children):
        child_path = f"{prefix}/{i}"
        out.update(_flatten(child, child_path))
    return out


def _match_key(snap: NodeSnapshot) -> str:
    if snap.resource_id:
        return f"id:{snap.resource_id}"
    label = snap.text or snap.content_desc
    if label:
        return f"label:{snap.class_name}:{label[:40]}"
    return f"path:{snap.path}"


def diff_xml(raw_baseline: str, raw_compare: str) -> XmlDiffResult:
    parser = AndroidXmlParser()
    tree_a, _ = parser.parse(raw_baseline)
    tree_b, _ = parser.parse(raw_compare)
    flat_a = _flatten(tree_a)
    flat_b = _flatten(tree_b)

    keys_a = {_match_key(v): v for v in flat_a.values()}
    keys_b = {_match_key(v): v for v in flat_b.values()}

    added: List[NodeSnapshot] = []
    removed: List[NodeSnapshot] = []
    changed: List[dict] = []
    unchanged = 0

    for key, snap_b in keys_b.items():
        snap_a = keys_a.get(key)
        if not snap_a:
            added.append(snap_b)
            continue
        if snap_a.signature() != snap_b.signature():
            changed.append({
                "key": key,
                "baseline": snap_a.__dict__,
                "compare": snap_b.__dict__,
                "fields": _changed_fields(snap_a, snap_b),
            })
        else:
            unchanged += 1

    for key, snap_a in keys_a.items():
        if key not in keys_b:
            removed.append(snap_a)

    return XmlDiffResult(
        baseline_node_count=len(flat_a),
        compare_node_count=len(flat_b),
        added=added,
        removed=removed,
        changed=changed,
        unchanged_count=unchanged,
    )


def _changed_fields(a: NodeSnapshot, b: NodeSnapshot) -> List[str]:
    fields = []
    for name in ("class_name", "resource_id", "text", "content_desc", "bounds", "clickable"):
        if getattr(a, name) != getattr(b, name):
            fields.append(name)
    return fields
