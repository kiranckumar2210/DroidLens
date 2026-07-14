"""Tests for custom locator builder."""

import pytest

from inspectiq.adapters.mock_adapter import MockAdapter, MOCK_ANDROID_XML
from inspectiq.domain.models import CustomLocatorRequest, CustomLocatorRule, Platform
from inspectiq.locator.uiautomator2 import CustomLocatorBuilder


@pytest.fixture
def tree():
    return MockAdapter(Platform.ANDROID).parse_ui_dump(MOCK_ANDROID_XML)


@pytest.fixture
def builder():
    return CustomLocatorBuilder()


def test_find_by_resource_id(builder, tree):
    result = builder.build(
        tree,
        CustomLocatorRequest(rules=[
            CustomLocatorRule(attribute="resource-id", operator="equals", value="com.demo.shop:id/loginBtn")
        ]),
    )
    assert result.match_count == 1
    assert "resource-id" in result.xpath or "loginBtn" in result.xpath
    assert "resourceId" in result.uiautomator2


def test_child_of_anchor(builder, tree):
    result = builder.build(
        tree,
        CustomLocatorRequest(
            rules=[CustomLocatorRule(attribute="text", operator="equals", value="Log In")],
            anchor_attribute="text",
            anchor_operator="equals",
            anchor_value="Welcome",
            relationship="inside",
        ),
    )
    assert result.xpath
    assert "descendant" in result.xpath or "Welcome" in result.xpath
