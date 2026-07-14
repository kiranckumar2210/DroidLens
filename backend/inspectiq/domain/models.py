"""Domain models for DroidLens."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Platform(str, Enum):
    ANDROID = "android"
    IOS = "ios"
    HARMONYOS = "harmonyos"


class LocatorType(str, Enum):
    ACCESSIBILITY_ID = "accessibility_id"
    RESOURCE_ID = "resource_id"
    ID = "id"
    TEXT = "text"
    CONTENT_DESC = "content_desc"
    CLASS_NAME = "class_name"
    UI_AUTOMATOR = "ui_automator"
    UIAUTOMATOR2 = "uiautomator2"
    XPATH = "xpath"
    XPATH_RELATIVE = "xpath_relative"
    XPATH_CONTAINS = "xpath_contains"
    XPATH_STARTS_WITH = "xpath_starts_with"
    XPATH_ENDS_WITH = "xpath_ends_with"
    XPATH_AXIS = "xpath_axis"
    XPATH_INDEX = "xpath_index"
    COMPOSITE = "composite"
    REGEX = "regex"
    IOS_PREDICATE = "ios_predicate"
    IOS_CLASS_CHAIN = "ios_class_chain"
    COORDINATE = "coordinate"
    NAME = "name"
    INSTANCE = "instance"
    BOUNDS = "bounds"


class ScriptLanguage(str, Enum):
    PYTHON = "python"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    CSHARP = "csharp"
    RUBY = "ruby"
    KOTLIN = "kotlin"


class LocatorBadge(str, Enum):
    RECOMMENDED = "recommended"
    GOOD = "good"
    FAIR = "fair"
    AVOID = "avoid"


class LocatorCategory(str, Enum):
    RESOURCE_ID = "resource_id"
    ACCESSIBILITY = "accessibility"
    TEXT = "text"
    CLASS_NAME = "class_name"
    PACKAGE = "package"
    INDEX = "index"
    UISELECTOR = "uiselector"
    XPATH = "xpath"
    RELATIVE = "relative"
    COMBINED = "combined"
    ADVANCED_XPATH = "advanced_xpath"
    COORDINATE = "coordinate"
    OTHER = "other"


class ScriptFramework(str, Enum):
    APPIUM = "appium"
    UIAUTOMATOR2 = "uiautomator2"
    SELENIUM = "selenium"
    ADB_SHELL = "adb_shell"


class SessionMode(str, Enum):
    LIVE = "live"
    OFFLINE = "offline"


class Bounds(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def center_x(self) -> int:
        return (self.x1 + self.x2) // 2

    @property
    def center_y(self) -> int:
        return (self.y1 + self.y2) // 2

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)

    def contains(self, x: int, y: int) -> bool:
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def to_string(self) -> str:
        return f"[{self.x1},{self.y1}][{self.x2},{self.y2}]"

    @classmethod
    def from_string(cls, s: str) -> Optional["Bounds"]:
        import re

        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", s.strip())
        if not m:
            return None
        return cls(x1=int(m.group(1)), y1=int(m.group(2)), x2=int(m.group(3)), y2=int(m.group(4)))


class ElementNode(BaseModel):
    """Normalized UI element — Android-first."""

    id: str = Field(default_factory=lambda: "")
    stable_key: Optional[str] = None
    platform: Platform = Platform.ANDROID
    class_name: str = ""
    text: Optional[str] = None
    resource_id: Optional[str] = None
    accessibility_id: Optional[str] = None
    content_desc: Optional[str] = None
    hint: Optional[str] = None
    name: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None
    type_name: Optional[str] = None
    package: Optional[str] = None
    bounds: Optional[Bounds] = None
    enabled: bool = True
    visible: bool = True
    clickable: bool = False
    scrollable: bool = False
    focusable: bool = False
    focused: bool = False
    checkable: bool = False
    checked: bool = False
    selected: bool = False
    password: bool = False
    long_clickable: bool = False
    drawing_order: Optional[int] = None
    index: int = 0
    instance: int = 0
    depth: int = 0
    is_flutter: bool = False
    flutter_semantics: Optional[str] = None
    raw_attributes: Dict[str, Any] = Field(default_factory=dict)
    children: List["ElementNode"] = Field(default_factory=list)
    parent_id: Optional[str] = None

    def display_type(self) -> str:
        if self.type_name:
            return self.type_name.replace("XCUIElementType", "")
        short = self.class_name.split(".")[-1] if self.class_name else "Unknown"
        return short

    def leaf_score(self) -> int:
        score = 0
        if not self.children:
            score += 10
        if self.text or self.label or self.value:
            score += 8
        if self.resource_id or self.accessibility_id or self.name:
            score += 6
        if self.clickable:
            score += 4
        if self.bounds:
            score -= self.bounds.area // 10000
        return score


class DeviceInfo(BaseModel):
    id: str
    platform: Platform
    name: str
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    os_version: Optional[str] = None
    sdk_version: Optional[str] = None
    status: str = "online"
    connection_type: str = "usb"
    serial: Optional[str] = None
    resolution: Optional[str] = None
    orientation: Optional[str] = None
    battery_level: Optional[int] = None
    is_emulator: bool = False


class AdbStatus(BaseModel):
    installed: bool
    path: Optional[str] = None
    version: Optional[str] = None
    server_running: bool = False
    device_count: int = 0
    unauthorized_count: int = 0
    offline_count: int = 0


class LocatorScore(BaseModel):
    stability: float = Field(ge=0, le=1)
    uniqueness: float = Field(ge=0, le=1)
    maintainability: float = Field(ge=0, le=1)
    overall: float = Field(ge=0, le=1)


class LocatorCandidate(BaseModel):
    locator_type: LocatorType
    value: str
    display_name: str
    scores: LocatorScore
    recommended: bool
    reason: str
    match_count: int = 1
    framework_hint: Optional[str] = None
    export_formats: Dict[str, str] = Field(default_factory=dict)
    performance_rating: Optional[str] = None  # fast, medium, slow
    robustness: Optional[str] = None  # high, medium, low
    valid: Optional[bool] = None
    category: Optional[str] = None
    badge: Optional[str] = None
    star_rating: Optional[float] = None
    layout_dependency: Optional[float] = None
    is_duplicate: bool = False


class XPathExample(BaseModel):
    axis: str
    xpath: str
    description: str


class CustomLocatorRule(BaseModel):
    attribute: str
    operator: str  # equals, contains, starts_with, ends_with, regex
    value: str
    combinator: Optional[str] = None  # AND, OR, NOT


class CustomLocatorRequest(BaseModel):
    rules: List[CustomLocatorRule]
    axis: Optional[str] = None  # child, parent, sibling, ancestor, descendant
    anchor_attribute: Optional[str] = None
    anchor_operator: Optional[str] = "equals"
    anchor_value: Optional[str] = None
    relationship: Optional[str] = None  # child_of, inside, sibling_after, sibling_before, below, above


class CustomLocatorResult(BaseModel):
    xpath: str
    uiautomator2: str
    match_count: int
    matched_elements: List[ElementNode] = Field(default_factory=list)


class ElementAnalysisContext(BaseModel):
    element_id: str
    hierarchy_level: int = 0
    ancestor_count: int = 0
    sibling_count: int = 0
    child_count: int = 0
    parent_class: Optional[str] = None
    parent_resource_id: Optional[str] = None
    is_in_recyclerview: bool = False
    is_in_scrollable: bool = False
    has_dynamic_text: bool = False
    has_dynamic_resource_id: bool = False
    duplicate_resource_ids_in_tree: int = 0
    stable_attributes: List[str] = Field(default_factory=list)


class LocatorSuggestion(BaseModel):
    severity: str = "info"
    category: str = "general"
    message: str
    hint: Optional[str] = None


class LocatorGroup(BaseModel):
    category: str
    label: str
    locators: List[LocatorCandidate] = Field(default_factory=list)


class LocatorBundle(BaseModel):
    element: ElementNode
    analysis: ElementAnalysisContext
    groups: List[LocatorGroup] = Field(default_factory=list)
    all_locators: List[LocatorCandidate] = Field(default_factory=list)
    suggestions: List[LocatorSuggestion] = Field(default_factory=list)
    recommended: Optional[LocatorCandidate] = None
    xpath_examples: List[XPathExample] = Field(default_factory=list)
    generation_ms: float = 0.0
    tree_hash: str = ""


class LocatorComparisonResult(BaseModel):
    locator_a: LocatorCandidate
    locator_b: LocatorCandidate
    matches_a: int
    matches_b: int
    overlap_count: int
    faster: Optional[str] = None
    more_stable: Optional[str] = None
    recommendation: str = ""


class ElementInspectionResult(BaseModel):
    element: ElementNode
    parent: Optional[ElementNode] = None
    children: List[ElementNode] = Field(default_factory=list)
    siblings_before: List[ElementNode] = Field(default_factory=list)
    siblings_after: List[ElementNode] = Field(default_factory=list)
    locators: List[LocatorCandidate] = Field(default_factory=list)
    xpath_examples: List[XPathExample] = Field(default_factory=list)
    coordinate_fallback: Optional[LocatorCandidate] = None
    hierarchy_level: int = 0
    analysis: Optional[ElementAnalysisContext] = None
    suggestions: List[LocatorSuggestion] = Field(default_factory=list)
    grouped_locators: List[LocatorGroup] = Field(default_factory=list)
    locator_bundle: Optional[LocatorBundle] = None


class InspectionSession(BaseModel):
    device_id: str
    platform: Platform
    mode: SessionMode = SessionMode.LIVE
    package: Optional[str] = None
    tree: Optional[ElementNode] = None
    screenshot_base64: Optional[str] = None
    raw_xml: Optional[str] = None
    screen_width: int = 0
    screen_height: int = 0
    screenshot_width: int = 0
    screenshot_height: int = 0
    rotation: int = 0
    scale_factor: float = 1.0
    coordinate_mapping: Optional[dict] = None
    last_refresh_ms: Optional[float] = None


class SaveElementRequest(BaseModel):
    project_name: str
    feature_name: str
    screen_name: str
    element_name: str
    platform: Platform
    element: ElementNode
    primary_locator: LocatorCandidate
    all_locators: List[LocatorCandidate] = Field(default_factory=list)
    screenshot_base64: Optional[str] = None
    xml_content: Optional[str] = None


class GeneratedScript(BaseModel):
    language: ScriptLanguage
    framework: ScriptFramework
    code: str
    locator_used: LocatorCandidate
    page_object: Optional[str] = None


class ProjectSummary(BaseModel):
    id: int
    name: str
    feature_count: int = 0
    element_count: int = 0
    created_at: datetime
