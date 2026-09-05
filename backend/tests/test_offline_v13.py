"""Tests for v1.3 locator validation, migration, and CLI."""

import json
import tempfile
from pathlib import Path

from inspectiq.cli import main as cli_main
from inspectiq.offline.locator_migrate import migrate_locator
from inspectiq.offline.locator_validate import validate_locators_against_xml

SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" class="android.widget.FrameLayout" resource-id="com.app:id/root">
    <node index="0" class="android.widget.Button" resource-id="com.app:id/login" text="Login" clickable="true"/>
  </node>
</hierarchy>"""

SAMPLE_V2 = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" class="android.widget.FrameLayout" resource-id="com.app:id/root">
    <node index="0" class="android.widget.Button" resource-id="com.app:id/login" text="Sign In" clickable="true"/>
  </node>
</hierarchy>"""

SUITE = {
    "format": "droidlens-locator-suite",
    "formatVersion": 1,
    "screens": [{
        "name": "Login",
        "elements": [
            {"name": "login_btn", "locator_type": "resource_id", "value": "com.app:id/login"},
        ],
    }],
}


def test_validate_locators_passes():
    report = validate_locators_against_xml(SAMPLE, SUITE, screen_name="Login")
    assert report.total == 1
    assert report.passed == 1
    assert report.ok


def test_validate_locators_fails_on_bad_id():
    bad = {"elements": [{"name": "x", "locator_type": "resource_id", "value": "com.app:id/missing"}]}
    report = validate_locators_against_xml(SAMPLE, bad)
    assert report.failed == 1
    assert not report.ok


def test_migrate_locator_still_unique():
    result = migrate_locator(SAMPLE, SAMPLE_V2, "resource_id", "com.app:id/login")
    assert result.status == "ok"


def test_cli_validate_locators(tmp_path: Path):
    xml = tmp_path / "Login.xml"
    suite = tmp_path / "locators.json"
    xml.write_text(SAMPLE, encoding="utf-8")
    suite.write_text(json.dumps(SUITE), encoding="utf-8")
    assert cli_main(["validate-locators", "--xml", str(xml), "--locators", str(suite)]) == 0
