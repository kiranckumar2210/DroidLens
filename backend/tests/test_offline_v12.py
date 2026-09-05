"""Tests for offline XML diff and locator health scan."""

from inspectiq.offline.locator_health import scan_xml_health
from inspectiq.offline.xml_diff import diff_xml

SAMPLE_A = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" class="android.widget.FrameLayout" resource-id="com.app:id/root" clickable="false">
    <node index="0" class="android.widget.Button" resource-id="com.app:id/login" text="Login" clickable="true"/>
  </node>
</hierarchy>"""

SAMPLE_B = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" class="android.widget.FrameLayout" resource-id="com.app:id/root" clickable="false">
    <node index="0" class="android.widget.Button" resource-id="com.app:id/login" text="Sign In" clickable="true"/>
    <node index="1" class="android.widget.TextView" resource-id="com.app:id/hint" text="Welcome" clickable="false"/>
  </node>
</hierarchy>"""


def test_xml_diff_detects_changes():
    result = diff_xml(SAMPLE_A, SAMPLE_B)
    assert result.compare_node_count > result.baseline_node_count
    assert result.added_count >= 1
    assert result.changed_count >= 1


def test_locator_health_flags_clickable_without_id():
    report = scan_xml_health(SAMPLE_A, "Login")
    assert report.node_count > 0
    assert report.score <= 100
