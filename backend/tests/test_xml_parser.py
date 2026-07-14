"""Tests for Android XML parser stable IDs."""

import pytest

from inspectiq.adapters.mock_adapter import MOCK_ANDROID_XML
from inspectiq.engine.xml_parser import AndroidXmlParser


@pytest.fixture
def parser():
    return AndroidXmlParser()


def test_stable_ids_across_parses(parser):
    tree1, _ = parser.parse(MOCK_ANDROID_XML)
    tree2, _ = parser.parse(MOCK_ANDROID_XML)

    def collect_ids(node, acc=None):
        if acc is None:
            acc = []
        acc.append(node.id)
        for c in node.children:
            collect_ids(c, acc)
        return acc

    assert collect_ids(tree1) == collect_ids(tree2)


def test_login_button_attributes(parser):
    tree, _ = parser.parse(MOCK_ANDROID_XML)

    def find_login(node):
        if node.text == "Login":
            return node
        for c in node.children:
            found = find_login(c)
            if found:
                return found
        return None

    btn = find_login(tree)
    assert btn is not None
    assert btn.resource_id == "com.demo.shop:id/loginBtn"
    assert btn.clickable is True
    assert btn.stable_key == btn.id


def test_pretty_format(parser):
    pretty = parser.pretty_format(MOCK_ANDROID_XML)
    assert "<hierarchy" in pretty
    assert "  " in pretty
