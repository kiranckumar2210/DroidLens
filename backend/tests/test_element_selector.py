"""Tests for smart element selection."""

import pytest

from inspectiq.adapters.mock_adapter import MockAdapter, MOCK_ANDROID_XML
from inspectiq.domain.models import Platform
from inspectiq.engine.element_selector import SmartElementSelector

@pytest.fixture
def android_tree():
    adapter = MockAdapter(Platform.ANDROID)
    return adapter.parse_ui_dump(MOCK_ANDROID_XML)


@pytest.fixture
def selector():
    return SmartElementSelector()


def test_select_login_button(selector, android_tree):
    # Login button bounds: [120,700][960,800]
    element = selector.find_at_coordinates(android_tree, 500, 750)
    assert element is not None
    assert element.text == "Login"
    assert element.resource_id == "com.demo.shop:id/loginBtn"
    assert "Button" in element.class_name


def test_select_textview_not_parent(selector, android_tree):
    # Submit text bounds: [400,900][680,960] — should get TextView not LinearLayout
    element = selector.find_at_coordinates(android_tree, 540, 930)
    assert element is not None
    assert element.text == "Submit"
    assert "TextView" in element.class_name


def test_parent_context(selector, android_tree):
    element = selector.find_at_coordinates(android_tree, 500, 750)
    ctx = selector.get_context(android_tree, element)
    assert ctx["parent"] is not None
    assert "LinearLayout" in ctx["parent"].class_name


def test_flatten_tree(selector, android_tree):
    nodes = selector.flatten(android_tree)
    assert len(nodes) > 5


CLICKABLE_PARENT_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" class="android.widget.FrameLayout" bounds="[0,0][1080,1920]">
    <node index="0" class="android.widget.LinearLayout" clickable="true"
          bounds="[100,100][500,200]">
      <node index="0" text="Shop" resource-id="com.app:id/shop_tab"
            class="android.widget.TextView" clickable="false"
            bounds="[100,100][500,200]"/>
    </node>
  </node>
</hierarchy>"""


def test_selects_child_over_clickable_parent(selector):
    adapter = MockAdapter(Platform.ANDROID)
    tree = adapter.parse_ui_dump(CLICKABLE_PARENT_XML)
    element = selector.find_at_coordinates(tree, 300, 150)
    assert element is not None
    assert element.resource_id == "com.app:id/shop_tab"
    assert element.text == "Shop"
    assert "TextView" in element.class_name

