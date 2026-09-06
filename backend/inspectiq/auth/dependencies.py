"""FastAPI dependencies for optional and required authentication."""

from __future__ import annotations

from typing import Callable, Optional

from fastapi import Depends, HTTPException, Header, Request

from inspectiq.auth.models import AuthUser, LicenseInfo
from inspectiq.auth.repository import create_auth_repository
from inspectiq.auth.services import AuthService, LicenseService, PaymentService, UserService, guest_license
from inspectiq.auth.admin_service import AdminService
from inspectiq.auth.system_settings_service import get_system_settings_service

_repo = create_auth_repository()
_auth = AuthService(_repo)
_license = LicenseService(_repo)
_user = UserService(_repo)
_payment = PaymentService(_repo)
_admin = AdminService(_repo)

FEATURE_FLAG_MAP = {
    "live_inspection": "live_inspector",
    "xml_upload": "xml_upload",
    "screenshot_upload": "screenshot_upload",
    "code_generator": "code_generator",
    "locator_builder": "locator_builder",
    "custom_locator_builder": "locator_builder",
    "export": "export",
    "interaction_recorder": "recorder",
    "ai_locator_suggestions": "ai_features",
    "session_save": "session_manager",
    "mock_demo": "mock_inspector",
}


def get_auth_service() -> AuthService:
    return _auth


def get_license_service() -> LicenseService:
    return _license


def get_user_service() -> UserService:
    return _user


def get_payment_service() -> PaymentService:
    return _payment


def get_admin_service() -> AdminService:
    return _admin


def configure_for_testing(repo=None) -> None:
    """Replace singleton services — used by unit tests only."""
    global _repo, _auth, _license, _user, _payment, _admin
    from inspectiq.auth import audit_log
    from inspectiq.auth.system_settings_service import configure_system_settings_repo
    _repo = repo or create_auth_repository()
    audit_log.configure_audit_repo(_repo)
    configure_system_settings_repo(_repo)
    get_system_settings_service().invalidate_cache()
    _auth = AuthService(_repo)
    _license = LicenseService(_repo)
    _user = UserService(_repo)
    _payment = PaymentService(_repo)
    _admin = AdminService(_repo)


async def optional_user(authorization: Optional[str] = Header(None)) -> Optional[AuthUser]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    return _auth.verify_token(token)


def _bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


async def require_user(user: Optional[AuthUser] = Depends(optional_user)) -> AuthUser:
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if user.status == "suspended":
        raise HTTPException(status_code=403, detail="Account suspended")
    return user


async def require_admin(user: AuthUser = Depends(require_user)) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def _check_feature_enabled(feature_key: Optional[str]) -> None:
    if not feature_key:
        return
    settings = get_system_settings_service().get_settings()
    flag_name = FEATURE_FLAG_MAP.get(feature_key, feature_key)
    if hasattr(settings.features, flag_name) and not getattr(settings.features, flag_name):
        raise HTTPException(status_code=403, detail=f"Feature '{feature_key}' is disabled by administrator")


async def require_premium(
    user: Optional[AuthUser] = Depends(optional_user),
    authorization: Optional[str] = Header(None),
    feature: Optional[str] = None,
) -> Optional[AuthUser]:
    _check_feature_enabled(feature)
    settings = get_system_settings_service().get_settings()
    token = _bearer_token(authorization)
    if not settings.subscription.subscription_enabled:
        return user
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not _license.has_premium_access(user.id, access_token=token):
        lic = _license.get_license(user.id, access_token=token)
        if lic.status.value == "trial_expired":
            raise HTTPException(
                status_code=403,
                detail="Your free trial has expired. Purchase a Lifetime License to continue.",
            )
        raise HTTPException(status_code=403, detail="Premium license required")
    return user


def require_premium_feature(feature: str) -> Callable:
    async def _dep(user: Optional[AuthUser] = Depends(optional_user)) -> Optional[AuthUser]:
        return await require_premium(user=user, feature=feature)
    return _dep


async def require_live_access(
    user: Optional[AuthUser] = Depends(optional_user),
    authorization: Optional[str] = Header(None),
) -> Optional[AuthUser]:
    settings = get_system_settings_service().get_settings()
    token = _bearer_token(authorization)
    _check_feature_enabled("live_inspection")

    if settings.subscription.login_required_for_live and settings.subscription.subscription_enabled:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required for live device access")
        if user.status == "suspended":
            raise HTTPException(status_code=403, detail="Account suspended")
        if settings.subscription.subscription_enabled and not _license.has_premium_access(user.id, access_token=token):
            lic = _license.get_license(user.id, access_token=token)
            if lic.status.value == "trial_expired":
                raise HTTPException(
                    status_code=403,
                    detail="Your free trial has expired. Purchase a Lifetime License to continue.",
                )
            raise HTTPException(status_code=403, detail="Premium license required")
        return user

    if user and user.status == "suspended":
        raise HTTPException(status_code=403, detail="Account suspended")
    if user and settings.subscription.subscription_enabled and not _license.has_premium_access(user.id, access_token=token):
        raise HTTPException(status_code=403, detail="Premium license required")
    return user


async def optional_license(user: Optional[AuthUser] = Depends(optional_user)) -> LicenseInfo:
    if not user:
        return guest_license()
    return _license.get_license(user.id)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
