"""Map between screenshot pixel coordinates and UI hierarchy bounds space."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from inspectiq.domain.models import Bounds, ElementNode


@dataclass
class CoordinateMapping:
    """Authoritative mapping between PNG screenshot pixels and XML hierarchy bounds."""

    device_width: int
    device_height: int
    hierarchy_width: int
    hierarchy_height: int
    screenshot_width: int
    screenshot_height: int
    scale_x: float
    scale_y: float
    offset_x: int = 0
    offset_y: int = 0
    rotation: int = 0

    def to_dict(self) -> dict:
        return {
            "device_width": self.device_width,
            "device_height": self.device_height,
            "hierarchy_width": self.hierarchy_width,
            "hierarchy_height": self.hierarchy_height,
            "screenshot_width": self.screenshot_width,
            "screenshot_height": self.screenshot_height,
            "scale_x": round(self.scale_x, 6),
            "scale_y": round(self.scale_y, 6),
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
            "rotation": self.rotation,
        }


def hierarchy_dimensions(tree: ElementNode, fallback: Tuple[int, int] = (1080, 1920)) -> Tuple[int, int]:
    """Infer hierarchy width/height from parsed XML bounds (max x2/y2)."""
    max_x = 0
    max_y = 0

    def walk(node: ElementNode) -> None:
        nonlocal max_x, max_y
        if node.bounds:
            max_x = max(max_x, node.bounds.x2)
            max_y = max(max_y, node.bounds.y2)
        for child in node.children:
            walk(child)

    walk(tree)
    w = max_x or fallback[0]
    h = max_y or fallback[1]
    return w, h


def hierarchy_origin(tree: ElementNode) -> Tuple[int, int]:
    """Root bounds origin — informational only; UIAutomator uses absolute screen coords."""
    if tree.bounds:
        return tree.bounds.x1, tree.bounds.y1
    return 0, 0


def build_coordinate_mapping(
    tree: Optional[ElementNode],
    device_size: Tuple[int, int],
    screenshot_size: Tuple[int, int],
    rotation: int = 0,
) -> CoordinateMapping:
    device_w, device_h = device_size
    screenshot_w, screenshot_h = screenshot_size
    fallback = device_size if device_w and device_h else (1080, 1920)
    hierarchy_w, hierarchy_h = hierarchy_dimensions(tree, fallback) if tree else fallback
    if not screenshot_w or not screenshot_h:
        screenshot_w, screenshot_h = hierarchy_w, hierarchy_h
    scale_x = hierarchy_w / screenshot_w if screenshot_w else 1.0
    scale_y = hierarchy_h / screenshot_h if screenshot_h else 1.0
    return CoordinateMapping(
        device_width=device_w or hierarchy_w,
        device_height=device_h or hierarchy_h,
        hierarchy_width=hierarchy_w,
        hierarchy_height=hierarchy_h,
        screenshot_width=screenshot_w,
        screenshot_height=screenshot_h,
        scale_x=scale_x,
        scale_y=scale_y,
        offset_x=0,
        offset_y=0,
        rotation=rotation,
    )


def screenshot_to_hierarchy(
    x: float,
    y: float,
    hierarchy_w: int,
    hierarchy_h: int,
    screenshot_w: int,
    screenshot_h: int,
) -> Tuple[int, int]:
    """Convert screenshot pixel coordinates to hierarchy/XML coordinate space."""
    if screenshot_w <= 0 or screenshot_h <= 0:
        return int(round(x)), int(round(y))
    hx = int(round(x * hierarchy_w / screenshot_w))
    hy = int(round(y * hierarchy_h / screenshot_h))
    hx = max(0, min(hx, max(hierarchy_w - 1, 0)))
    hy = max(0, min(hy, max(hierarchy_h - 1, 0)))
    return hx, hy


def hierarchy_to_screenshot_bounds(
    bounds: Bounds,
    mapping: CoordinateMapping,
) -> Bounds:
    sx = mapping.screenshot_width / mapping.hierarchy_width if mapping.hierarchy_width else 1.0
    sy = mapping.screenshot_height / mapping.hierarchy_height if mapping.hierarchy_height else 1.0
    return Bounds(
        x1=int(round((bounds.x1 - mapping.offset_x) * sx)),
        y1=int(round((bounds.y1 - mapping.offset_y) * sy)),
        x2=int(round((bounds.x2 - mapping.offset_x) * sx)),
        y2=int(round((bounds.y2 - mapping.offset_y) * sy)),
    )


def hierarchy_to_screenshot_pct(
    bounds: Bounds,
    hierarchy_w: int,
    hierarchy_h: int,
) -> dict[str, str]:
    """CSS percentage overlay within a screenshot-sized box (non-uniform scale safe)."""
    if hierarchy_w <= 0 or hierarchy_h <= 0:
        hierarchy_w = hierarchy_w or 1
        hierarchy_h = hierarchy_h or 1
    return {
        "left": f"{(bounds.x1 / hierarchy_w) * 100}%",
        "top": f"{(bounds.y1 / hierarchy_h) * 100}%",
        "width": f"{((bounds.x2 - bounds.x1) / hierarchy_w) * 100}%",
        "height": f"{((bounds.y2 - bounds.y1) / hierarchy_h) * 100}%",
    }


def bounds_debug_info(bounds: Bounds) -> dict:
    return {
        "bounds": [bounds.x1, bounds.y1, bounds.x2, bounds.y2],
        "width": bounds.x2 - bounds.x1,
        "height": bounds.y2 - bounds.y1,
        "center_x": (bounds.x1 + bounds.x2) // 2,
        "center_y": (bounds.y1 + bounds.y2) // 2,
    }
