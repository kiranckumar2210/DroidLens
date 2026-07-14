"""Production API paths — spec aliases without breaking /auth/* compatibility."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

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
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    OrderStatusResponse,
    PaymentActionResult,
    PlanPublic,
    PricingResponse,
    PurchaseRequest,
    PurchaseResult,
    RefreshRequest,
    RegisterRequest,
    UpdateProfileRequest,
)
from inspectiq.auth.plans import list_purchasable_plans
from inspectiq.auth.services import AuthService, LicenseService, PaymentService, UserService
from inspectiq.api.auth_routes import _account_summary

router = APIRouter(tags=["v1"])


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
def refresh(req: RefreshRequest, auth: AuthService = Depends(get_auth_service)):
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


@router.get("/profile", response_model=AccountSummary)
def profile(
    user=Depends(require_user),
    user_svc: UserService = Depends(get_user_service),
    license_svc: LicenseService = Depends(get_license_service),
):
    return _account_summary(user, user_svc, license_svc)


@router.patch("/profile", response_model=AccountSummary)
def update_profile(
    req: UpdateProfileRequest,
    user=Depends(require_user),
    user_svc: UserService = Depends(get_user_service),
    license_svc: LicenseService = Depends(get_license_service),
):
    user_svc.update_profile(user.id, req)
    return _account_summary(user, user_svc, license_svc)


@router.get("/license")
def license(
    user=Depends(require_user),
    license_svc: LicenseService = Depends(get_license_service),
):
    info = license_svc.get_license(user.id)
    return {
        "license": info,
        "license_cache": sign_license_cache(user.id, info),
    }


@router.get("/pricing", response_model=PricingResponse)
def pricing():
    cfg = get_auth_config()
    plans = [
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
    return PricingResponse(
        lifetime_price_inr=cfg.lifetime_price_inr,
        currency=cfg.currency,
        payment_provider=cfg.payment_provider,
        trial_days=cfg.trial_days,
        plans=plans,
    )


@router.post("/payment/create-order", response_model=PurchaseResult)
def create_order(
    req: PurchaseRequest,
    user=Depends(require_user),
    payment_svc: PaymentService = Depends(get_payment_service),
):
    try:
        return payment_svc.create_purchase(user.id, req.plan_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payment/order/{payment_id}", response_model=PurchaseResult)
def get_order(
    payment_id: str,
    user=Depends(require_user),
    payment_svc: PaymentService = Depends(get_payment_service),
):
    try:
        return payment_svc.get_checkout(user.id, payment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/payment/status/{payment_id}", response_model=OrderStatusResponse)
def payment_status(
    payment_id: str,
    user=Depends(require_user),
    payment_svc: PaymentService = Depends(get_payment_service),
):
    try:
        return payment_svc.sync_order_status(user.id, payment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payment/verify")
def verify_payment(
    body: dict,
    user=Depends(require_user),
    payment_svc: PaymentService = Depends(get_payment_service),
):
    payment_id = body.get("payment_id") or body.get("order_id")
    if not payment_id:
        raise HTTPException(status_code=400, detail="payment_id required")
    cfg = get_auth_config()
    try:
        if cfg.payment_provider == "phonepe":
            result = payment_svc.sync_order_status(user.id, payment_id)
            return PaymentActionResult(
                payment_id=result.payment_id,
                status=result.status,
                license=result.license,
            )
        license_info = payment_svc.confirm_purchase(user.id, payment_id)
        return payment_svc.payment_action_result(user.id, payment_id, license_info)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payment/fail", response_model=PaymentActionResult)
def fail_payment(
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


@router.post("/payment/cancel", response_model=PaymentActionResult)
def cancel_payment(
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


@router.post("/payment/webhook")
def payment_webhook(
    payload: dict,
    authorization: Optional[str] = Header(None),
    payment_svc: PaymentService = Depends(get_payment_service),
):
    try:
        result = payment_svc.handle_webhook(payload, authorization=authorization)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    if not result:
        return {"status": "ignored"}
    return {"status": "processed", "order": result}
