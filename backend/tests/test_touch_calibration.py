"""Tests for touch coordinate calibration."""

from inspectiq.recording.touch_calibration import TouchCalibration


def test_touch_calibration_from_props():
    props = """
add device 1: /dev/input/event2
  name:     "touchscreen"
  ABS_MT_POSITION_X     : value 0, min 0, max 1079, fuzz 0, flat 0, resolution 0
  ABS_MT_POSITION_Y     : value 0, min 0, max 2399, fuzz 0, flat 0, resolution 0
"""
    wm = "Physical size: 1080x2400"
    cal = TouchCalibration.from_getevent_props(props, wm)
    assert cal.screen_width == 1080
    assert cal.screen_height == 2400
    sx, sy = cal.to_screen(540, 1200)
    assert sx == 540
    assert sy == 1200


def test_touch_calibration_scales_high_res_raw():
    props = """
  ABS_MT_POSITION_X     : value 0, min 0, max 32767, fuzz 0, flat 0, resolution 0
  ABS_MT_POSITION_Y     : value 0, min 0, max 32767, fuzz 0, flat 0, resolution 0
"""
    wm = "Override size: 1080x1920"
    cal = TouchCalibration.from_getevent_props(props, wm)
    sx, sy = cal.to_screen(16384, 16384)
    assert 500 <= sx <= 560
    assert 900 <= sy <= 980
