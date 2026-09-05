"""Tests for iOS XML parser."""

from inspectiq.adapters.mock_adapter import MOCK_IOS_XML
from inspectiq.engine.ios_parser import IOSXmlParser
from inspectiq.domain.models import Platform


def test_ios_parser_builds_tree():
    tree = IOSXmlParser().parse(MOCK_IOS_XML)
    assert tree.platform == Platform.IOS
    assert tree.class_name == "XCUIElementTypeApplication"
    assert len(tree.children) == 1
    login_btn = None
    for node in tree.children[0].children:
        if node.name == "login":
            login_btn = node
    assert login_btn is not None
    assert login_btn.text == "Login"
    assert login_btn.bounds is not None
    assert login_btn.bounds.x2 == 370


def test_ios_parser_accessibility_id():
    tree = IOSXmlParser().parse(MOCK_IOS_XML)
    fields = [c for c in tree.children[0].children if c.name == "username"]
    assert len(fields) == 1
    assert fields[0].accessibility_id == "username"
