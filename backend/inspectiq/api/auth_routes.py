"""Authentication and licensing REST API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from inspectiq.auth.config import get_auth_config
from inspectiq.auth.dependencies import (
    get_auth_service,
    get_license_service,
    get_payment_service,
    get_user_service,
    require_user,
)
from inspectiq.auth.license_cache import sign_license_cache
from inspectiq.auth.models import (
    AccountSummary,
    AuthResult,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    PaymentActionResult,
    PlanPublic,
    PricingResponse,
    PurchaseRequest,
    PurchaseResult,
    RefreshRequest,
    RegisterRequest,
    UpdateProfileRequest,
)
from inspectiq.auth.plans import get_plans_sorted, list_purchasable_plans
from inspectiq.auth.services import AuthService, LicenseService, PaymentService, UserService
from inspectiq.auth.system_settings_models import SystemConfigPublic
from inspectiq.auth.system_settings_service import get_system_settings_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _account_summary(user, user_svc: UserService, license_svc: LicenseService) -> AccountSummary:
    profile = user_svc.get_profile(user.id)
    license_info = license_svc.get_license(user.id)
    history = user_svc.get_purchase_history(user.id)
    return AccountSummary(
        user=profile,
        license=license_info,
        purchase_history=history,
        license_cache=sign_license_cache(user.id, license_info),
    )


@router.post("/register", response_model=AuthResult)
def register(req: RegisterRequest, auth: AuthService = Depends(get_auth_service)):
    try:
        return auth.register(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=AuthResult)
def login(req: LoginRequest, auth: AuthService = Depends(get_auth_service)):
    try:
        return auth.login(req)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh", response_model=AuthResult)
def refresh_token(req: RefreshRequest, auth: AuthService = Depends(get_auth_service)):
    try:
        return auth.refresh(req.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
def logout(
    req: LogoutRequest,
    user=Depends(require_user),
    auth: AuthService = Depends(get_auth_service),
):
    auth.logout(user.id, req.refresh_token)
    return {"status": "ok"}


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, auth: AuthService = Depends(get_auth_service)):
    return auth.forgot_password(req.email)


@router.get("/me", response_model=AccountSummary)
def account_summary(
    user=Depends(require_user),
    license_svc: LicenseService = Depends(get_license_service),
    user_svc: UserService = Depends(get_user_service),
):
    return _account_summary(user, user_svc, license_svc)


@router.patch("/me", response_model=AccountSummary)
def update_profile(
    req: UpdateProfileRequest,
    user=Depends(require_user),
    license_svc: LicenseService = Depends(get_license_service),
    user_svc: UserService = Depends(get_user_service),
):
    user_svc.update_profile(user.id, req)
    return _account_summary(user, user_svc, license_svc)


@router.post("/change-password")
def change_password(req: ChangePasswordRequest, user=Depends(require_user), auth: AuthService = Depends(get_auth_service)):
    try:
        auth.change_password(user.id, req.current_password, req.new_password)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delete-account")
def delete_account(body: dict, user=Depends(require_user), auth: AuthService = Depends(get_auth_service)):
    password = body.get("password", "")
    if not password:
        raise HTTPException(status_code=400, detail="Password required")
    try:
        auth.delete_account(user.id, password)
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/license")
def get_license(user=Depends(require_user), license_svc: LicenseService = Depends(get_license_service)):
    info = license_svc.get_license(user.id)
    return {
        "license": info,
        "license_cache": sign_license_cache(user.id, info),
    }


@router.get("/system-config", response_model=SystemConfigPublic)
def get_system_config():
    return get_system_settings_service().get_public_config()


@router.get("/pricing", response_model=PricingResponse)
def get_pricing():
    settings = get_system_settings_service().get_settings()
    cfg = get_auth_config()
    lifetime_price = settings.payment.lifetime_price_inr or cfg.lifetime_price_inr
    currency = settings.payment.currency or cfg.currency
    trial_days = settings.payment.trial_days or cfg.trial_days
    plans = [
        PlanPublic(
            id=p.id,
            name=p.name,
            description=p.description,
            price_inr=p.price_inr if p.id != "lifetime" else lifetime_price,
            billing_period=p.billing_period,
            trial_days=trial_days if p.id == "trial" else p.trial_days,
            features=p.features,
        )
        for p in list_purchasable_plans()
    ]
    return PricingResponse(
        lifetime_price_inr=lifetime_price,
        currency=currency,
        payment_provider=cfg.payment_provider,
        trial_days=trial_days,
        plans=plans,
    )


@router.get("/plans", response_model=list[PlanPublic])
def list_plans():
    return [
        PlanPublic(
            id=p.id,
            name=p.name,
            description=p.description,
            price_inr=p.price_inr,
            billing_period=p.billing_period,
            trial_days=p.trial_days,
            features=p.features,
        )
        for p in get_plans_sorted()
        if p.active and p.id != "guest"
    ]


@router.post("/purchase", response_model=PurchaseResult)
def create_purchase(
    req: PurchaseRequest,
    user=Depends(require_user),
    payment_svc: PaymentService = Depends(get_payment_service),
):
    try:
        return payment_svc.create_purchase(user.id, req.plan_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/purchase/{payment_id}", response_model=PurchaseResult)
def get_purchase(
    payment_id: str,
    user=Depends(require_user),
    payment_svc: PaymentService = Depends(get_payment_service),
):
    try:
        return payment_svc.get_checkout(user.id, payment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/purchase/confirm", response_model=PaymentActionResult)
def confirm_purchase(
    body: dict,
    user=Depends(require_user),
    payment_svc: PaymentService = Depends(get_payment_service),
):
    payment_id = body.get("payment_id")
    if not payment_id:
        raise HTTPException(status_code=400, detail="payment_id required")
    try:
        license_info = payment_svc.confirm_purchase(user.id, payment_id)
        return payment_svc.payment_action_result(user.id, payment_id, license_info)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/purchase/fail", response_model=PaymentActionResult)
def fail_purchase(
    body: dict,
    user=Depends(require_user),
    payment_svc: PaymentService = Depends(get_payment_service),
):
    payment_id = body.get("payment_id")
    if not payment_id:
        raise HTTPException(status_code=400, detail="payment_id required")
    try:
        license_info = payment_svc.fail_purchase(user.id, payment_id)
        return payment_svc.payment_action_result(user.id, payment_id, license_info)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/purchase/cancel", response_model=PaymentActionResult)
def cancel_purchase(
    body: dict,
    user=Depends(require_user),
    payment_svc: PaymentService = Depends(get_payment_service),
):
    payment_id = body.get("payment_id")
    if not payment_id:
        raise HTTPException(status_code=400, detail="payment_id required")
    try:
        license_info = payment_svc.cancel_purchase(user.id, payment_id)
        return payment_svc.payment_action_result(user.id, payment_id, license_info)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/plans/purchasable", response_model=list[PlanPublic])
def purchasable_plans():
    return [
        PlanPublic(
            id=p.id,
            name=p.name,
            description=p.description,
            price_inr=p.price_inr,
            billing_period=p.billing_period,
            trial_days=p.trial_days,
            features=p.features,
        )
        for p in list_purchasable_plans()
    ]
