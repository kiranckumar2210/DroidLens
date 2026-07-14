"""Admin dashboard REST API — requires admin role."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from inspectiq.auth.admin_models import (
    AdminActionResult,
    AdminDashboardResponse,
    AdminUserDetail,
    AdminUserRow,
    AdminUserUpdate,
    PaginatedPayments,
    PaginatedUsers,
    PaymentStats,
    RegistrationStats,
    RevenueStats,
    SubscriptionStats,
)
from inspectiq.auth.admin_service import AdminService
from inspectiq.auth.dependencies import get_admin_service, get_client_ip, require_admin
from inspectiq.auth.models import AuthUser
from inspectiq.auth.system_settings_models import SetLicenseRequest, SystemSettings, SystemSettingsUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    _admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    return svc.get_dashboard()


@router.get("/users", response_model=PaginatedUsers)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    license: Optional[str] = None,
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    _admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    return svc.list_users(
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status,
        license_filter=license,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/users/count")
def count_users(
    _admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    return {"count": svc.count_users()}


@router.get("/users/recent", response_model=list[AdminUserRow])
def recent_users(
    limit: int = Query(10, ge=1, le=50),
    _admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    return svc.get_recent_users(limit)


@router.get("/users/export")
def export_users(
    search: Optional[str] = None,
    status: Optional[str] = None,
    license: Optional[str] = None,
    _admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    csv_data = svc.export_users_csv(
        search=search,
        status_filter=status,
        license_filter=license,
    )
    return PlainTextResponse(
        csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"},
    )


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_user(
    user_id: str,
    _admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    try:
        return svc.get_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/users/{user_id}", response_model=AdminUserDetail)
def update_user(
    user_id: str,
    req: AdminUserUpdate,
    admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    try:
        return svc.update_user(admin.id, user_id, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/users/{user_id}", response_model=AdminActionResult)
def delete_user(
    user_id: str,
    admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    try:
        return svc.delete_user(admin.id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/{user_id}/reset-trial", response_model=AdminActionResult)
def reset_trial(
    user_id: str,
    admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    try:
        return svc.reset_trial(admin.id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/{user_id}/activate-license", response_model=AdminActionResult)
def activate_license(
    user_id: str,
    admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    try:
        return svc.activate_license(admin.id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/{user_id}/suspend", response_model=AdminActionResult)
def suspend_user(
    user_id: str,
    admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    try:
        return svc.suspend_user(admin.id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/{user_id}/set-license", response_model=AdminActionResult)
def set_user_license(
    user_id: str,
    req: SetLicenseRequest,
    admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    try:
        return svc.set_license(admin.id, user_id, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/settings/licensing", response_model=SystemSettings)
def get_licensing_settings(
    _admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    return svc.get_licensing_settings()


@router.patch("/settings/licensing", response_model=SystemSettings)
def update_licensing_settings(
    req: SystemSettingsUpdate,
    request: Request,
    admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    return svc.update_licensing_settings(
        admin.id,
        admin.email,
        req,
        ip=get_client_ip(request),
    )


@router.get("/payments", response_model=PaginatedPayments)
def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    _admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    return svc.list_payments(
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/revenue", response_model=RevenueStats)
def revenue_stats(
    period: str = Query("30d"),
    _admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    return svc.get_revenue(period)


@router.get("/subscriptions", response_model=SubscriptionStats)
def subscription_stats(
    _admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    return svc.get_subscriptions()


@router.get("/activity")
def activity_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    _admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    return svc.list_activity(page=page, page_size=page_size, action=action, user_id=user_id)


@router.get("/statistics")
def statistics(
    _admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    return svc.get_statistics()


@router.get("/payments/export")
def export_payments(
    search: Optional[str] = None,
    status: Optional[str] = None,
    _admin: AuthUser = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    csv_data = svc.export_payments_csv(search=search, status_filter=status)
    return PlainTextResponse(
        csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=payments.csv"},
    )
