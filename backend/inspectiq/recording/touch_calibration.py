"""Map raw getevent touch coordinates to screen pixels."""

from __future__ import annotations

import re
from dataclasses import dataclass

_MT_X = re.compile(r"ABS_MT_POSITION_X\s*:.*?max\s+(\d+)", re.I | re.S)
_MT_Y = re.compile(r"ABS_MT_POSITION_Y\s*:.*?max\s+(\d+)", re.I | re.S)
_ABS_X = re.compile(r"\bABS_X\s*:.*?max\s+(\d+)", re.I | re.S)
_ABS_Y = re.compile(r"\bABS_Y\s*:.*?max\s+(\d+)", re.I | re.S)
_WM_SIZE = re.compile(r"(\d+)\s*x\s*(\d+)")


@dataclass
class TouchCalibration:
    raw_max_x: int = 32767
    raw_max_y: int = 32767
    screen_width: int = 1080
    screen_height: int = 1920

    @classmethod
    def from_getevent_props(cls, props_text: str, wm_size_text: str) -> "TouchCalibration":
        raw_max_x = _first_int(_MT_X, props_text) or _first_int(_ABS_X, props_text) or 32767
        raw_max_y = _first_int(_MT_Y, props_text) or _first_int(_ABS_Y, props_text) or 32767
        screen_w, screen_h = 1080, 1920
        m = _WM_SIZE.search(wm_size_text.replace(",", ""))
        if m:
            screen_w, screen_h = int(m.group(1)), int(m.group(2))
        return cls(raw_max_x=raw_max_x, raw_max_y=raw_max_y, screen_width=screen_w, screen_height=screen_h)

    def to_screen(self, raw_x: int, raw_y: int) -> tuple[int, int]:
        sx = _scale(raw_x, self.raw_max_x, self.screen_width)
        sy = _scale(raw_y, self.raw_max_y, self.screen_height)
        return (
            min(max(sx, 0), max(self.screen_width - 1, 0)),
            min(max(sy, 0), max(self.screen_height - 1, 0)),
        )


def _first_int(pattern: re.Pattern[str], text: str) -> int | None:
    m = pattern.search(text)
    return int(m.group(1)) if m else None


def _scale(raw: int, raw_max: int, screen: int) -> int:
    if raw_max <= 0:
        return raw
    # Many devices report max equal to (screen - 1); treat as 1:1 in that case.
    if raw_max <= screen + 5:
        return raw
    return int(raw * screen / raw_max)
