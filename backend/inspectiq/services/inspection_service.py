"""Inspection orchestration — live devices and offline uploads."""

from __future__ import annotations

import base64
import os
import time
import uuid
from pathlib import Path
from typing import List, Optional

from inspectiq.adapters.base import PlatformAdapter, get_adapter
from inspectiq.adapters.android_adapter import AndroidAdapter
from inspectiq.adapters.mock_adapter import MockAdapter
from inspectiq.codegen.multi_language_generator import MultiLanguageCodeGenerator
from inspectiq.codegen.script_generator import ScriptGenerator
from inspectiq.codegen.uiautomator2_generator import UiAutomator2CodeGenerator
from inspectiq.domain.models import (
    CustomLocatorRequest,
    CustomLocatorResult,
    ElementInspectionResult,
    ElementNode,
    GeneratedScript,
    InspectionSession,
    LocatorBundle,
    LocatorCandidate,
    LocatorComparisonResult,
    Platform,
    ScriptFramework,
    ScriptLanguage,
    SessionMode,
)
from inspectiq.engine.coordinate_mapper import (
    bounds_debug_info,
    build_coordinate_mapping,
    hierarchy_dimensions,
    screenshot_to_hierarchy,
)
from inspectiq.engine.element_selector import SmartElementSelector
from inspectiq.engine.xml_parser import AndroidXmlParser
from inspectiq.locator.engine import LocatorEngine
from inspectiq.locator.raw_validator import RawLocatorValidator
from inspectiq.locator.uiautomator2 import CustomLocatorBuilder
from inspectiq.locator.xpath_builder import XPathBuilder
from inspectiq.logging_config import get_logger

logger = get_logger(__name__)

MOCK_DEVICE_PREFIX = "mock-"


class InspectionService:
    """Orchestrates inspection sessions. Live and mock data paths are strictly separated."""

    def __init__(self):
        self._sessions: dict = {}
        self._selector = SmartElementSelector()
        self._locator_engine = LocatorEngine()
        self._xpath_builder = XPathBuilder()
        self._script_gen = ScriptGenerator()
        self._u2_gen = UiAutomator2CodeGenerator()
        self._multi_gen = MultiLanguageCodeGenerator()
        self._custom_builder = CustomLocatorBuilder()
        self._raw_validator = RawLocatorValidator()
        self._xml_parser = AndroidXmlParser()
        self._android = AndroidAdapter()

    @staticmethod
    def is_mock_device(device_id: str) -> bool:
        return device_id.startswith(MOCK_DEVICE_PREFIX)

    def _adapter_for(self, platform: Platform, device_id: str) -> PlatformAdapter:
        """Return the correct adapter — mock devices only via explicit mock IDs."""
        if self.is_mock_device(device_id):
            logger.debug("Using mock adapter for device_id=%s", device_id)
            return get_adapter(platform, use_mock=True)
        if platform == Platform.ANDROID:
            return self._android
        return get_adapter(platform, use_mock=False)

    async def list_devices(self, platform: Platform):
        return await get_adapter(platform, use_mock=False).list_devices()

    async def connect_live_device(self, device_id: str, platform: Platform) -> None:
        if self.is_mock_device(device_id):
            raise ValueError(
                f"Device '{device_id}' is a mock ID. Use POST /session/mock for sample data."
            )
        adapter = self._adapter_for(platform, device_id)
        logger.info("Connecting live device: serial=%s platform=%s", device_id, platform.value)
        await adapter.connect(device_id)
        logger.info("Live device connected: serial=%s", device_id)

    async def refresh_session(
        self, device_id: str, platform: Platform, package: Optional[str] = None
    ) -> InspectionSession:
        if self.is_mock_device(device_id):
            raise RuntimeError(
                f"Cannot live-refresh mock device '{device_id}'. Load mock via /session/mock."
            )

        t0 = time.monotonic()
        adapter = self._adapter_for(platform, device_id)
        logger.info("Live refresh started: serial=%s", device_id)

        logger.debug("Capturing UI hierarchy: serial=%s", device_id)
        raw_xml = await adapter.dump_ui(device_id)
        if not raw_xml or ("<?xml" not in raw_xml and "<hierarchy" not in raw_xml):
            raise RuntimeError("UI dump returned empty or invalid XML")
        logger.info("UI hierarchy captured: serial=%s bytes=%d", device_id, len(raw_xml))

        logger.debug("Capturing screenshot: serial=%s", device_id)
        screenshot_bytes = await adapter.screenshot(device_id)
        if not screenshot_bytes:
            raise RuntimeError("Screenshot capture returned empty data")
        logger.info("Screenshot captured: serial=%s bytes=%d", device_id, len(screenshot_bytes))

        if os.environ.get("DROIDLENS_DEBUG_SCREENSHOT", "").lower() in ("1", "true", "yes"):
            debug_dir = Path(os.environ.get("DROIDLENS_DEBUG_DIR", "/tmp/droidlens-screenshots"))
            debug_dir.mkdir(parents=True, exist_ok=True)
            debug_path = debug_dir / f"{device_id}_{int(time.time())}.png"
            debug_path.write_bytes(screenshot_bytes)
            logger.info("Debug screenshot saved: %s", debug_path)

        device_w, device_h = await adapter.get_screen_size(device_id)
        screenshot_width, screenshot_height = device_w, device_h
        rotation = 0
        tree = None

        if isinstance(adapter, AndroidAdapter):
            screenshot_width, screenshot_height = adapter.get_adb().png_dimensions(screenshot_bytes)
            tree, rotation = adapter.parse_with_rotation(raw_xml)
        else:
            tree = adapter.parse_ui_dump(raw_xml)

        hierarchy_w, hierarchy_h = hierarchy_dimensions(tree, (device_w, device_h)) if tree else (device_w, device_h)
        coord_map = build_coordinate_mapping(
            tree,
            (device_w, device_h),
            (screenshot_width or hierarchy_w, screenshot_height or hierarchy_h),
            rotation,
        )

        elapsed = round((time.monotonic() - t0) * 1000, 1)
        session = InspectionSession(
            device_id=device_id,
            platform=platform,
            mode=SessionMode.LIVE,
            package=package,
            tree=tree,
            screenshot_base64=base64.b64encode(screenshot_bytes).decode("ascii"),
            raw_xml=raw_xml,
            screen_width=hierarchy_w,
            screen_height=hierarchy_h,
            screenshot_width=screenshot_width or hierarchy_w,
            screenshot_height=screenshot_height or hierarchy_h,
            rotation=rotation,
            scale_factor=coord_map.scale_x,
            coordinate_mapping=coord_map.to_dict(),
            last_refresh_ms=elapsed,
        )
        self._sessions[device_id] = session
        logger.info(
            "Live session updated: serial=%s device=%dx%d hierarchy=%dx%d screenshot=%dx%d "
            "scale=(%.4f,%.4f) rotation=%d elapsed_ms=%s",
            device_id,
            coord_map.device_width, coord_map.device_height,
            hierarchy_w, hierarchy_h,
            screenshot_width or hierarchy_w, screenshot_height or hierarchy_h,
            coord_map.scale_x, coord_map.scale_y, rotation, elapsed,
        )
        return session

    async def refresh_hierarchy_for_recording(
        self, device_id: str, platform: Platform = Platform.ANDROID
    ) -> Optional[InspectionSession]:
        """Fast UI-only refresh used between recorded device taps."""
        if self.is_mock_device(device_id):
            return self.get_session(device_id)

        existing = self.get_session(device_id)
        if not existing or not existing.tree:
            return await self.refresh_session(device_id, platform)

        adapter = self._adapter_for(platform, device_id)
        try:
            raw_xml = await adapter.dump_ui(device_id)
            if not raw_xml or "<hierarchy" not in raw_xml:
                return existing

            if isinstance(adapter, AndroidAdapter):
                tree, rotation = adapter.parse_with_rotation(raw_xml)
                existing.rotation = rotation
            else:
                tree = adapter.parse_ui_dump(raw_xml)

            device_w, device_h = await adapter.get_screen_size(device_id)
            hierarchy_w, hierarchy_h = (
                hierarchy_dimensions(tree, (device_w, device_h)) if tree else (device_w, device_h)
            )
            existing.tree = tree
            existing.raw_xml = raw_xml
            existing.screen_width = hierarchy_w
            existing.screen_height = hierarchy_h
            shot_w = existing.screenshot_width or hierarchy_w
            shot_h = existing.screenshot_height or hierarchy_h
            if tree:
                coord_map = build_coordinate_mapping(
                    tree, (device_w, device_h), (shot_w, shot_h), existing.rotation
                )
                existing.coordinate_mapping = coord_map.to_dict()
                existing.scale_factor = coord_map.scale_x
            self._sessions[device_id] = existing
            return existing
        except Exception as exc:
            logger.warning("Hierarchy refresh for recording failed: serial=%s err=%s", device_id, exc)
            return existing

    def create_offline_session(
        self,
        raw_xml: Optional[str] = None,
        screenshot_base64: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> InspectionSession:
        sid = session_id or f"offline-{uuid.uuid4().hex[:8]}"
        logger.info("Creating offline session: id=%s", sid)
        tree = None
        rotation = 0
        screen_w, screen_h = 1080, 1920
        screenshot_w, screenshot_h = screen_w, screen_h

        if raw_xml:
            tree, rotation = self._xml_parser.parse(raw_xml)

        if screenshot_base64:
            png = base64.b64decode(screenshot_base64)
            from inspectiq.adb.manager import AdbManager
            screenshot_w, screenshot_h = AdbManager.png_dimensions(png)
            if screenshot_w:
                screen_w, screen_h = screenshot_w, screenshot_h

        if tree and tree.bounds and tree.bounds.x2:
            screen_w = max(screen_w, tree.bounds.x2)
            screen_h = max(screen_h, tree.bounds.y2)
        hierarchy_w, hierarchy_h = hierarchy_dimensions(tree, (screen_w, screen_h)) if tree else (screen_w, screen_h)
        coord_map = build_coordinate_mapping(
            tree,
            (screen_w, screen_h),
            (screenshot_w, screenshot_h),
            rotation,
        )

        session = InspectionSession(
            device_id=sid,
            platform=Platform.ANDROID,
            mode=SessionMode.OFFLINE,
            tree=tree,
            screenshot_base64=screenshot_base64,
            raw_xml=raw_xml,
            screen_width=hierarchy_w,
            screen_height=hierarchy_h,
            screenshot_width=screenshot_w,
            screenshot_height=screenshot_h,
            rotation=rotation,
            scale_factor=coord_map.scale_x,
            coordinate_mapping=coord_map.to_dict(),
        )
        self._sessions[sid] = session
        return session

    def get_session(self, device_id: str) -> Optional[InspectionSession]:
        return self._sessions.get(device_id)

    def inspect_element_by_id(self, device_id: str, element_id: str) -> Optional[ElementInspectionResult]:
        session = self.get_session(device_id)
        if not session or not session.tree:
            return None
        element = self._selector.find_by_id(session.tree, element_id)
        if not element:
            element = self._find_by_stable_key(session.tree, element_id)
        if not element:
            return None
        return self._build_inspection(session.tree, element)

    def _find_by_stable_key(self, tree: ElementNode, key: str) -> Optional[ElementNode]:
        for n in self._selector.flatten(tree):
            if n.stable_key == key or n.id == key:
                return n
        return None

    def inspect_element_at(
        self,
        device_id: str,
        x: int,
        y: int,
        *,
        coord_space: str = "screenshot",
    ) -> Optional[ElementInspectionResult]:
        session = self.get_session(device_id)
        if not session or not session.tree:
            return None

        hierarchy_w = session.screen_width or 1
        hierarchy_h = session.screen_height or 1
        screenshot_w = session.screenshot_width or hierarchy_w
        screenshot_h = session.screenshot_height or hierarchy_h

        if coord_space == "device":
            mapping = session.coordinate_mapping or {}
            device_w = mapping.get("device_width") or screenshot_w or hierarchy_w
            device_h = mapping.get("device_height") or screenshot_h or hierarchy_h
            if device_w <= 0 or device_h <= 0:
                hx, hy = int(round(x)), int(round(y))
            else:
                hx = int(round(x * hierarchy_w / device_w))
                hy = int(round(y * hierarchy_h / device_h))
        else:
            hx, hy = screenshot_to_hierarchy(
                float(x), float(y),
                hierarchy_w, hierarchy_h,
                screenshot_w, screenshot_h,
            )
        element = self._selector.find_at_coordinates(session.tree, hx, hy)
        if element and element.bounds:
            logger.info(
                "select_at: serial=%s screenshot=(%d,%d) hierarchy=(%d,%d) "
                "dims hierarchy=%dx%d screenshot=%dx%d scale=(%.4f,%.4f) "
                "element=%s bounds=%s center=(%d,%d)",
                device_id, x, y, hx, hy,
                hierarchy_w, hierarchy_h, screenshot_w, screenshot_h,
                hierarchy_w / screenshot_w if screenshot_w else 1.0,
                hierarchy_h / screenshot_h if screenshot_h else 1.0,
                element.text or element.resource_id or element.class_name,
                bounds_debug_info(element.bounds),
                (element.bounds.x1 + element.bounds.x2) // 2,
                (element.bounds.y1 + element.bounds.y2) // 2,
            )
        else:
            logger.info(
                "select_at: serial=%s screenshot=(%d,%d) hierarchy=(%d,%d) — no element",
                device_id, x, y, hx, hy,
            )
        if not element:
            return None
        return self._build_inspection(session.tree, element)

    def _build_inspection(self, tree: ElementNode, element: ElementNode) -> ElementInspectionResult:
        ctx = self._selector.get_context(tree, element)
        bundle = self._locator_engine.generate_bundle(element, tree)
        coordinate = next((l for l in bundle.all_locators if l.locator_type.value == "coordinate"), None)

        return ElementInspectionResult(
            element=element,
            parent=ctx["parent"],
            children=ctx["children"],
            siblings_before=ctx["siblings_before"],
            siblings_after=ctx["siblings_after"],
            locators=bundle.all_locators,
            xpath_examples=bundle.xpath_examples,
            coordinate_fallback=coordinate,
            hierarchy_level=element.depth,
            analysis=bundle.analysis,
            suggestions=bundle.suggestions,
            grouped_locators=bundle.groups,
            locator_bundle=bundle,
        )

    def get_locator_bundle(self, device_id: str, element_id: str) -> Optional[LocatorBundle]:
        session = self.get_session(device_id)
        if not session or not session.tree:
            return None
        element = self._selector.find_by_id(session.tree, element_id)
        if not element:
            element = self._find_by_stable_key(session.tree, element_id)
        if not element:
            return None
        return self._locator_engine.generate_bundle(element, session.tree)

    def compare_locators(
        self,
        device_id: str,
        locator_a: LocatorCandidate,
        locator_b: LocatorCandidate,
    ) -> Optional[LocatorComparisonResult]:
        session = self.get_session(device_id)
        if not session or not session.tree:
            return None
        return self._locator_engine.compare_locators(session.tree, locator_a, locator_b)

    def build_custom_locator(self, device_id: str, request: CustomLocatorRequest) -> Optional[CustomLocatorResult]:
        session = self.get_session(device_id)
        if not session or not session.tree:
            return None
        return self._custom_builder.build(session.tree, request)

    async def load_mock_session(self) -> InspectionSession:
        """Load bundled mock XML + screenshot — never used for live inspection."""
        logger.info("Loading mock sample session")
        adapter = MockAdapter(Platform.ANDROID)
        device_id = "mock-android-001"
        raw_xml = await adapter.dump_ui(device_id)
        screenshot_bytes = await adapter.screenshot(device_id)
        tree = adapter.parse_ui_dump(raw_xml)
        session = InspectionSession(
            device_id=device_id,
            platform=Platform.ANDROID,
            mode=SessionMode.OFFLINE,
            tree=tree,
            screenshot_base64=base64.b64encode(screenshot_bytes).decode("ascii"),
            raw_xml=raw_xml,
            screen_width=1080,
            screen_height=1920,
            screenshot_width=1080,
            screenshot_height=1920,
        )
        self._sessions[device_id] = session
        logger.info("Mock session ready: id=%s", device_id)
        return session

    def validate_raw_locator(self, device_id: str, locator_type: str, expression: str) -> Optional[dict]:
        session = self.get_session(device_id)
        if not session or not session.tree:
            return None
        return self._raw_validator.validate(session.tree, locator_type, expression)

    def preview_locator(self, device_id: str, locator_type: str, value: str) -> Optional[dict]:
        session = self.get_session(device_id)
        if not session or not session.tree:
            return None
        return self._locator_engine.preview(session.tree, locator_type, value)

    def generate_script(
        self,
        locator: LocatorCandidate,
        language: ScriptLanguage = ScriptLanguage.PYTHON,
        framework: ScriptFramework = ScriptFramework.UIAUTOMATOR2,
        action: str = "click",
        page_name: str = "LoginPage",
        element_name: str = "login_button",
        text_value: str = "your_text",
        language_profile: str = "python_uiautomator2",
        package_name: str = "com.example.app",
    ) -> GeneratedScript:
        if language_profile and language_profile != "python_uiautomator2":
            return self._multi_gen.generate(
                locator, language_profile, action, element_name, page_name, text_value, package_name
            )
        if framework == ScriptFramework.UIAUTOMATOR2:
            return self._u2_gen.generate(locator, action, element_name, page_name, text_value)
        return self._script_gen.generate(locator, language, framework, action, page_name, element_name)

    def search_tree(
        self, device_id: str, query: str, search_type: str = "all"
    ) -> List[ElementNode]:
        session = self.get_session(device_id)
        if not session or not session.tree:
            return []
        q = query.lower()
        results = []
        for n in self._selector.flatten(session.tree):
            if search_type == "text" and q not in (n.text or "").lower():
                continue
            if search_type == "resource-id" and q not in (n.resource_id or "").lower():
                continue
            if search_type == "class" and q not in (n.class_name or "").lower():
                continue
            if search_type == "xpath" and q not in (n.resource_id or n.text or "").lower():
                continue
            if search_type == "bounds" and q not in (n.bounds.to_string() if n.bounds else ""):
                continue
            if search_type == "all":
                hay = " ".join(filter(None, [
                    n.text, n.resource_id, n.class_name, n.content_desc,
                    n.package, n.bounds.to_string() if n.bounds else "",
                ])).lower()
                if q not in hay:
                    continue
            results.append(n)
        return results

    def pretty_xml(self, device_id: str) -> Optional[str]:
        session = self.get_session(device_id)
        if not session or not session.raw_xml:
            return None
        return self._xml_parser.pretty_format(session.raw_xml)

    def export_locators_json(self, device_id: str, element_id: str) -> Optional[dict]:
        result = self.inspect_element_by_id(device_id, element_id)
        if not result:
            return None
        return {
            "element": result.element.model_dump(mode="json"),
            "locators": [l.model_dump(mode="json") for l in result.locators],
        }
