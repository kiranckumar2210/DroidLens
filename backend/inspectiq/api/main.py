"""DroidLens FastAPI application."""

from __future__ import annotations

import inspectiq.bootstrap  # noqa: F401 — patch sqlite3 before SQLAlchemy

import os
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from inspectiq.api.auth_routes import router as auth_router
from inspectiq.api.admin_routes import router as admin_router
from inspectiq.api.recording_routes import configure_recording_engine, router as recording_router
from inspectiq.api.v1_routes import router as v1_router
from inspectiq.auth.dependencies import require_premium, require_live_access
from inspectiq.auth.models import AuthUser

from inspectiq.api.websocket import LiveRefreshManager
from inspectiq.logging_config import get_logger, setup_logging
from inspectiq.config import use_mock_mode
from inspectiq.domain.models import (
    CustomLocatorRequest,
    GeneratedScript,
    InspectionSession,
    LocatorBundle,
    LocatorCandidate,
    LocatorComparisonResult,
    Platform,
    SaveElementRequest,
    ScriptFramework,
    ScriptLanguage,
)
from inspectiq.adb.manager import AdbError
from inspectiq.services.device_service import DeviceService
from inspectiq.services.inspection_service import InspectionService
from inspectiq.storage.database import StorageService

USE_MOCK = os.environ.get("DROIDLENS_MOCK", os.environ.get("INSPECTIQ_MOCK", "")).lower() in ("1", "true", "yes")
if os.environ.get("DROIDLENS_MOCK") is None and os.environ.get("INSPECTIQ_MOCK") is None:
    USE_MOCK = use_mock_mode()

setup_logging(os.environ.get("DROIDLENS_LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

app = FastAPI(
    title="DroidLens API",
    description="Professional Android UI Inspector for uiautomator2 automation",
    version="1.0.0",
)

_DESKTOP_CORS_ORIGINS = (
    "http://127.0.0.1:8765",
    "http://localhost:8765",
)

_cors_raw = os.environ.get("DROIDLENS_CORS_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()] or ["*"]
_use_wildcard = "*" in _cors_origins
if _use_wildcard:
    _cors_origins = ["*"]
    _cors_allow_credentials = False
else:
    for _origin in _DESKTOP_CORS_ORIGINS:
        if _origin not in _cors_origins:
            _cors_origins.append(_origin)
    _cors_allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(v1_router)

inspection = InspectionService()
configure_recording_engine(inspection)
app.include_router(recording_router)
devices_svc = DeviceService()
storage = StorageService()
live_refresh = LiveRefreshManager(inspection)


class ConnectRequest(BaseModel):
    device_id: str
    platform: Platform = Platform.ANDROID
    package: Optional[str] = None


class SelectRequest(BaseModel):
    device_id: str
    x: int
    y: int


class SelectByIdRequest(BaseModel):
    device_id: str
    element_id: str


class LaunchRequest(BaseModel):
    device_id: str
    platform: Platform = Platform.ANDROID
    package: str
    activity: Optional[str] = None


class GenerateScriptRequest(BaseModel):
    locator: LocatorCandidate
    language: ScriptLanguage = ScriptLanguage.PYTHON
    framework: ScriptFramework = ScriptFramework.UIAUTOMATOR2
    language_profile: str = "python_uiautomator2"
    action: str = "click"
    page_name: str = "LoginPage"
    element_name: str = "login_button"
    text_value: str = "your_text"
    package_name: str = "com.example.app"


class RawLocatorValidateRequest(BaseModel):
    device_id: str
    locator_type: str = "xpath"
    expression: str


class LocatorPreviewRequest(BaseModel):
    device_id: str
    locator_type: str
    value: str


class LocatorCompareRequest(BaseModel):
    device_id: str
    locator_a: LocatorCandidate
    locator_b: LocatorCandidate


class LocatorBundleRequest(BaseModel):
    device_id: str
    element_id: str


class OfflineUploadRequest(BaseModel):
    xml_content: Optional[str] = None
    screenshot_base64: Optional[str] = None
    session_id: Optional[str] = None


class WifiConnectRequest(BaseModel):
    host: str
    port: int = 5555


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    adb = await devices_svc.adb_status()
    return {
        "status": "ok",
        "product": "DroidLens",
        "mock_mode": USE_MOCK,
        "adb": adb.model_dump(),
    }


@app.get("/adb/status")
async def adb_status():
    return await devices_svc.adb_status()


@app.post("/adb/restart")
async def adb_restart():
    return await devices_svc.restart_adb()


@app.post("/adb/kill")
async def adb_kill():
    await devices_svc.kill_adb()
    return {"status": "killed"}


@app.post("/adb/connect-wifi")
async def adb_connect_wifi(req: WifiConnectRequest):
    try:
        return await devices_svc.connect_wifi(req.host, req.port)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/adb/disconnect-wifi")
async def adb_disconnect_wifi(host: Optional[str] = None):
    return await devices_svc.disconnect_wifi(host)


@app.get("/devices")
async def list_devices(platform: Platform = Platform.ANDROID, refresh: bool = False):
    if platform != Platform.ANDROID:
        devices = await inspection.list_devices(platform)
    elif refresh:
        devices = await devices_svc.refresh_devices()
    else:
        devices = await devices_svc.list_android_devices()
    logger.info("List devices: count=%d refresh=%s", len(devices), refresh)
    return {"devices": devices, "mock_mode": USE_MOCK, "live_only": True}


@app.get("/devices/{device_id}/packages")
async def list_packages(device_id: str, q: str = ""):
    try:
        packages = await devices_svc.list_packages(device_id, q)
        return {"packages": packages}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/session/connect")
async def connect_session(req: ConnectRequest, _user: AuthUser = Depends(require_live_access)):
    try:
        await devices_svc.validate_device_for_live(req.device_id)
    except Exception as e:
        logger.warning("Live connect rejected: serial=%s reason=%s", req.device_id, e)
        raise HTTPException(status_code=503, detail=str(e))
    try:
        await inspection.connect_live_device(req.device_id, req.platform)
        session = await inspection.refresh_session(req.device_id, req.platform, req.package)
        if session.mode.value != "live":
            raise HTTPException(status_code=500, detail="Session was not created in live mode")
        logger.info("Live session started: serial=%s mode=%s", req.device_id, session.mode.value)
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AdbError as e:
        logger.error("Live connect ADB error: serial=%s %s", req.device_id, e)
        raise HTTPException(status_code=502, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/session/refresh")
async def refresh_session(req: ConnectRequest, _user: AuthUser = Depends(require_live_access)):
    try:
        await devices_svc.validate_device_for_live(req.device_id)
        session = await inspection.refresh_session(req.device_id, req.platform, req.package)
        logger.info("Live refresh complete: serial=%s ms=%s", req.device_id, session.last_refresh_ms)
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AdbError as e:
        logger.error("Live refresh ADB error: serial=%s %s", req.device_id, e)
        raise HTTPException(status_code=502, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/session/offline")
async def create_offline_session(req: OfflineUploadRequest, _user: AuthUser = Depends(require_premium)):
    if not req.xml_content and not req.screenshot_base64:
        raise HTTPException(status_code=400, detail="Provide xml_content and/or screenshot_base64")
    try:
        return inspection.create_offline_session(
            req.xml_content, req.screenshot_base64, req.session_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid upload: {e}")


@app.post("/session/offline/upload")
async def upload_offline_files(
    xml_file: Optional[UploadFile] = File(None),
    screenshot_file: Optional[UploadFile] = File(None),
    _user: AuthUser = Depends(require_premium),
):
    xml_content = None
    screenshot_b64 = None
    if xml_file:
        raw = await xml_file.read()
        xml_content = raw.decode("utf-8", errors="replace")
    if screenshot_file:
        import base64
        data = await screenshot_file.read()
        screenshot_b64 = base64.b64encode(data).decode("ascii")
    if not xml_content and not screenshot_b64:
        raise HTTPException(status_code=400, detail="Upload at least one file")
    try:
        return inspection.create_offline_session(xml_content, screenshot_b64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/session/{device_id}")
async def get_session(device_id: str):
    session = inspection.get_session(device_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session")
    return session


@app.get("/session/{device_id}/xml")
async def get_pretty_xml(device_id: str):
    xml = inspection.pretty_xml(device_id)
    if not xml:
        raise HTTPException(status_code=404, detail="No XML in session")
    return {"xml": xml}


@app.post("/inspect/select")
async def select_at_coordinates(req: SelectRequest):
    result = inspection.inspect_element_at(req.device_id, req.x, req.y)
    if not result:
        raise HTTPException(status_code=404, detail="No element at coordinates")
    return result


@app.post("/inspect/select-by-id")
async def select_by_id(req: SelectByIdRequest):
    result = inspection.inspect_element_by_id(req.device_id, req.element_id)
    if not result:
        raise HTTPException(status_code=404, detail="Element not found")
    return result


@app.get("/inspect/search")
async def search_tree(
    device_id: str,
    q: str = Query(..., min_length=1),
    type: str = Query("all", alias="type"),
):
    results = inspection.search_tree(device_id, q, type)
    return {"results": results, "count": len(results)}


@app.post("/locator/custom")
async def custom_locator(device_id: str, request: CustomLocatorRequest, _user: AuthUser = Depends(require_premium)):
    result = inspection.build_custom_locator(device_id, request)
    if not result:
        raise HTTPException(status_code=404, detail="No session or no matches")
    return result


@app.post("/app/launch")
async def launch_app(req: LaunchRequest):
    adapter = inspection._adapter(req.platform)
    try:
        await adapter.launch_app(req.device_id, req.package, req.activity)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "launched", "package": req.package}


@app.post("/locator/validate-raw")
async def validate_raw_locator(req: RawLocatorValidateRequest):
    result = inspection.validate_raw_locator(req.device_id, req.locator_type, req.expression)
    if result is None:
        raise HTTPException(status_code=404, detail="No active session")
    return result


@app.post("/locator/preview")
async def preview_locator(req: LocatorPreviewRequest):
    result = inspection.preview_locator(req.device_id, req.locator_type, req.value)
    if result is None:
        raise HTTPException(status_code=404, detail="No active session")
    return result


@app.get("/locator/bundle/{device_id}/{element_id}")
async def get_locator_bundle(device_id: str, element_id: str) -> LocatorBundle:
    bundle = inspection.get_locator_bundle(device_id, element_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Element or session not found")
    return bundle


@app.post("/locator/bundle")
async def post_locator_bundle(req: LocatorBundleRequest) -> LocatorBundle:
    bundle = inspection.get_locator_bundle(req.device_id, req.element_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Element or session not found")
    return bundle


@app.post("/locator/compare")
async def compare_locators(req: LocatorCompareRequest) -> LocatorComparisonResult:
    result = inspection.compare_locators(req.device_id, req.locator_a, req.locator_b)
    if not result:
        raise HTTPException(status_code=404, detail="No active session")
    return result


@app.post("/session/mock")
async def load_mock_session():
    return await inspection.load_mock_session()


@app.post("/code/generate")
async def generate_code(req: GenerateScriptRequest, _user: AuthUser = Depends(require_premium)) -> GeneratedScript:
    return inspection.generate_script(
        req.locator, req.language, req.framework, req.action,
        req.page_name, req.element_name, req.text_value,
        req.language_profile, req.package_name,
    )


@app.get("/export/locators/{device_id}/{element_id}")
async def export_locators(device_id: str, element_id: str, _user: AuthUser = Depends(require_premium)):
    data = inspection.export_locators_json(device_id, element_id)
    if not data:
        raise HTTPException(status_code=404, detail="Element not found")
    return data


@app.post("/storage/save")
async def save_element(req: SaveElementRequest, _user: AuthUser = Depends(require_premium)):
    return storage.save_element(req)


@app.get("/storage/projects")
async def list_projects():
    return {"projects": storage.list_projects()}


@app.get("/storage/repository/export")
async def export_locator_repository(
    format: str = Query("json", alias="format"),
    _user: AuthUser = Depends(require_premium),
):
    from inspectiq.storage.export_formats import format_repository

    rows = storage.export_repository()
    content, media_type, filename = format_repository(rows, format)
    return Response(
        content=content.encode("utf-8"),
        media_type=f"{media_type}; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/storage/repository")
async def get_locator_repository(_user: AuthUser = Depends(require_premium)):
    return {"elements": storage.export_repository()}


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await live_refresh.handle(websocket)


def _mount_frontend_static() -> None:
    """Serve built React SPA when DROIDLENS_STATIC_DIR is set (Railway / Docker production)."""
    static_dir = os.environ.get("DROIDLENS_STATIC_DIR")
    if not static_dir:
        return
    root = Path(static_dir)
    if not root.is_dir():
        logger.warning("DROIDLENS_STATIC_DIR=%s does not exist — skipping static mount", static_dir)
        return

    index_html = root / "index.html"
    if not index_html.is_file():
        logger.warning("No index.html in %s — skipping static mount", static_dir)
        return

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        if full_path:
            candidate = root / full_path
            if candidate.is_file():
                return FileResponse(candidate)
        return FileResponse(index_html)

    logger.info("Serving frontend from %s", root)


_mount_frontend_static()


def main():
    import uvicorn
    port = int(
        os.environ.get("PORT")
        or os.environ.get("DROIDLENS_PORT")
        or os.environ.get("INSPECTIQ_PORT", "8765")
    )
    host = os.environ.get("DROIDLENS_HOST", "127.0.0.1")
    uvicorn.run("inspectiq.api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
