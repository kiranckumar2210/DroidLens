"""Parse iOS XCUI / Appium accessibility XML into ElementNode trees."""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from typing import Optional

from inspectiq.domain.models import Bounds, ElementNode, Platform


class IOSXmlParser:
    """Parse WDA / idevice_ui / Appium page source XML."""

    def parse(self, raw: str) -> ElementNode:
        root_el = ET.fromstring(raw)
        return self._parse_node(root_el)

    def _parse_node(self, el: ET.Element, parent_id: Optional[str] = None) -> ElementNode:
        node_id = str(uuid.uuid4())
        attrs = el.attrib

        x = int(float(attrs.get("x", 0)))
        y = int(float(attrs.get("y", 0)))
        w = int(float(attrs.get("width", 0)))
        h = int(float(attrs.get("height", 0)))
        bounds = Bounds(x1=x, y1=y, x2=x + w, y2=y + h) if w and h else None

        label = attrs.get("label") or None
        name = attrs.get("name") or attrs.get("identifier") or None
        value = attrs.get("value") or None
        type_name = el.tag if el.tag.startswith("XCUI") else attrs.get("type", el.tag)

        node = ElementNode(
            id=node_id,
            platform=Platform.IOS,
            class_name=type_name or "",
            type_name=type_name,
            label=label,
            name=name,
            value=value,
            text=label or value,
            accessibility_id=name,
            bounds=bounds,
            enabled=attrs.get("enabled", "true").lower() == "true",
            visible=attrs.get("visible", "true").lower() == "true",
            clickable=attrs.get("accessible", "false").lower() == "true",
            raw_attributes=dict(attrs),
            parent_id=parent_id,
        )
        for child_el in el:
            node.children.append(self._parse_node(child_el, node_id))
        return node
