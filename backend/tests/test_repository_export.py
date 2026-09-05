"""Tests for locator repository export formatting."""

from inspectiq.storage.export_formats import format_repository, repository_to_csv, repository_to_json


def test_repository_json_format():
    rows = [{
        "project": "App",
        "feature": "Login",
        "screen": "LoginPage",
        "platform": "android",
        "element_name": "login_btn",
        "class_name": "Button",
        "bounds": "0,0,100,50",
        "captured_at": None,
        "primary_locator": {"locator_type": "resource_id", "value": "com.app:id/login", "overall": 0.9},
        "locators": [{"locator_type": "resource_id", "value": "com.app:id/login", "overall": 0.9, "is_primary": True, "recommended": True, "reason": "unique"}],
    }]
    content, mime, name = format_repository(rows, "json")
    assert "droidlens-locator-repository" in content
    assert mime == "application/json"
    assert name.endswith(".json")


def test_repository_csv_has_header():
    rows = [{
        "project": "App",
        "feature": "Login",
        "screen": "LoginPage",
        "platform": "android",
        "element_name": "btn",
        "class_name": "Button",
        "bounds": "",
        "captured_at": None,
        "primary_locator": None,
        "locators": [{"locator_type": "xpath", "value": "//Button", "overall": 0.5, "is_primary": True, "recommended": False, "reason": ""}],
    }]
    csv = repository_to_csv(rows)
    assert "project,feature,screen" in csv
    assert "//Button" in csv
