"""Tests for ADB screenshot capture helpers."""

from inspectiq.adb.manager import AdbManager


def test_normalize_png_valid():
    header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    assert AdbManager._normalize_png(header).startswith(b"\x89PNG")


def test_normalize_png_crlf_corruption():
    # Simulate Android pipe bug: newlines in PNG become CRLF
    raw = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + b"IDAT\r\n" + b"data\nmore"
    fixed = AdbManager._normalize_png(raw)
    assert fixed.startswith(b"\x89PNG")
    assert b"\r\n" not in fixed or fixed.startswith(b"\x89PNG\r\n\x1a\n")


def test_normalize_png_leading_junk():
    raw = b"WARNING\n" + b"\x89PNG\r\n\x1a\n" + b"\x00" * 10
    assert AdbManager._normalize_png(raw).startswith(b"\x89PNG")


SAMPLE_DUMPSYS_DISPLAY = """
  mViewports=[DisplayViewport{type=INTERNAL, valid=true, isActive=true, displayId=0, uniqueId='local:4630947043778501779', physicalPort=147, orientation=0, logicalFrame=Rect(0, 0 - 1224, 2992), physicalFrame=Rect(0, 0 - 1224, 2992), deviceWidth=1224, deviceHeight=2992}, DisplayViewport{type=INTERNAL, valid=true, isActive=false, displayId=1, uniqueId='local:4630947043778501780', physicalPort=148, orientation=2, logicalFrame=Rect(0, 0 - 1080, 1272), physicalFrame=Rect(0, 0 - 1080, 1272), deviceWidth=1080, deviceHeight=1272}]
"""


def test_parse_active_display_id_from_dumpsys():
    import re
    active = re.search(r"isActive=true[^}]*uniqueId='local:(\d+)'", SAMPLE_DUMPSYS_DISPLAY)
    assert active
    assert active.group(1) == "4630947043778501779"
