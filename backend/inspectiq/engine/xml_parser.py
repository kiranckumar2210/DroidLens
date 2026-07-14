"""Android UIAutomator XML parser with stable element IDs."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from inspectiq.domain.models import Bounds, ElementNode, Platform


class AndroidXmlParser:
    """Parse UIAutomator hierarchy XML into ElementNode tree."""

    FLUTTER_HINTS = ("flutter", "io.flutter", "FlutterView")

    def parse(self, raw: str) -> Tuple[ElementNode, int]:
        raw = self._normalize_raw(raw)
        root_el = ET.fromstring(raw)
        rotation = int(root_el.attrib.get("rotation", "0")) if root_el.tag == "hierarchy" else 0
        instance_counters: Dict[str, int] = {}

        def stable_id(path: str, el: ET.Element, index: int) -> str:
            key = "|".join([
                path,
                el.attrib.get("class", ""),
                el.attrib.get("resource-id", ""),
                el.attrib.get("bounds", ""),
                el.attrib.get("text", "")[:32],
                str(index),
            ])
            return hashlib.sha256(key.encode()).hexdigest()[:16]

        def parse_node(
            el: ET.Element,
            parent_id: Optional[str],
            path: str,
            depth: int,
            index: int,
        ) -> ElementNode:
            class_name = el.attrib.get("class", "")
            bounds = Bounds.from_string(el.attrib.get("bounds", ""))
            resource_id = el.attrib.get("resource-id") or None
            if resource_id == "":
                resource_id = None
            content_desc = el.attrib.get("content-desc") or None
            if content_desc == "":
                content_desc = None
            text = el.attrib.get("text") or None
            if text == "":
                text = None

            inst_key = f"{class_name}|{resource_id}|{text}"
            instance_counters[inst_key] = instance_counters.get(inst_key, -1) + 1
            instance = instance_counters[inst_key]

            node_path = f"{path}/{class_name.split('.')[-1]}[{index}]"
            node_id = stable_id(path, el, index)

            pkg = el.attrib.get("package") or None
            is_flutter = any(h in (class_name + (pkg or "")) for h in self.FLUTTER_HINTS)

            accessibility_id = content_desc or resource_id

            node = ElementNode(
                id=node_id,
                stable_key=node_id,
                platform=Platform.ANDROID,
                class_name=class_name,
                text=text,
                resource_id=resource_id,
                accessibility_id=accessibility_id,
                content_desc=content_desc,
                hint=el.attrib.get("hint") or None,
                package=pkg,
                bounds=bounds,
                enabled=el.attrib.get("enabled", "true") == "true",
                visible=el.attrib.get("visible-to-user", "true") == "true",
                clickable=el.attrib.get("clickable", "false") == "true",
                scrollable=el.attrib.get("scrollable", "false") == "true",
                focusable=el.attrib.get("focusable", "false") == "true",
                focused=el.attrib.get("focused", "false") == "true",
                checkable=el.attrib.get("checkable", "false") == "true",
                checked=el.attrib.get("checked", "false") == "true",
                selected=el.attrib.get("selected", "false") == "true",
                password=el.attrib.get("password", "false") == "true",
                long_clickable=el.attrib.get("long-clickable", "false") == "true",
                drawing_order=int(el.attrib.get("drawing-order", "0") or 0) or None,
                index=int(el.attrib.get("index", str(index))),
                instance=instance,
                depth=depth,
                is_flutter=is_flutter,
                flutter_semantics=content_desc if is_flutter else None,
                raw_attributes=dict(el.attrib),
                parent_id=parent_id,
            )

            for i, child_el in enumerate(el):
                if isinstance(child_el.tag, str):
                    node.children.append(parse_node(child_el, node_id, node_path, depth + 1, i))

            return node

        if root_el.tag == "hierarchy":
            children = [c for c in root_el if isinstance(c.tag, str)]
            if not children:
                return ElementNode(id="root", platform=Platform.ANDROID, class_name="hierarchy"), rotation
            if len(children) == 1:
                return parse_node(children[0], None, "/hierarchy", 0, 0), rotation
            root = ElementNode(id="root", stable_key="root", platform=Platform.ANDROID, class_name="hierarchy")
            for i, child_el in enumerate(children):
                root.children.append(parse_node(child_el, root.id, "/hierarchy", 1, i))
            return root, rotation

        return parse_node(root_el, None, "/root", 0, 0), rotation

    @staticmethod
    def _normalize_raw(raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("UI hierchary dumped to") or raw.startswith("UI hierarchy dumped to"):
            idx = raw.find("<?xml")
            if idx >= 0:
                return raw[idx:]
        return raw

    @staticmethod
    def pretty_format(raw: str) -> str:
        try:
            raw = AndroidXmlParser._normalize_raw(raw)
            root = ET.fromstring(raw)
            if hasattr(ET, "indent"):
                ET.indent(root, space="  ")
                return ET.tostring(root, encoding="unicode")
            # Python 3.8 fallback
            from xml.dom import minidom
            rough = ET.tostring(root, encoding="unicode")
            return minidom.parseString(rough).toprettyxml(indent="  ")
        except ET.ParseError:
            return raw
