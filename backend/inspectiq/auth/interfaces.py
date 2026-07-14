"""Abstract service interfaces — swap providers without changing consumers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from inspectiq.auth.models import (
    AuthResult,
    AuthUser,
    LicenseInfo,
    LoginRequest,
    PaymentActionResult,
    PurchaseResult,
    RegisterRequest,
    UpdateProfileRequest,
)


class AuthenticationService(ABC):
    @abstractmethod
    def register(self, req: RegisterRequest) -> AuthResult:
        ...

    @abstractmethod
    def login(self, req: LoginRequest) -> AuthResult:
        ...

    @abstractmethod
    def refresh(self, refresh_token: str) -> AuthResult:
        ...

    @abstractmethod
    def logout(self, user_id: str, refresh_token: Optional[str] = None) -> None:
        ...

    @abstractmethod
    def forgot_password(self, email: str) -> dict:
        ...

    @abstractmethod
    def verify_token(self, token: str) -> Optional[AuthUser]:
        ...

    @abstractmethod
    def change_password(self, user_id: str, current: str, new_password: str) -> None:
        ...

    @abstractmethod
    def delete_account(self, user_id: str, password: str) -> None:
        ...


class UserService(ABC):
    @abstractmethod
    def get_profile(self, user_id: str) -> AuthUser:
        ...

    @abstractmethod
    def update_profile(self, user_id: str, req: UpdateProfileRequest) -> AuthUser:
        ...


class LicenseService(ABC):
    @abstractmethod
    def get_license(self, user_id: str) -> LicenseInfo:
        ...

    @abstractmethod
    def has_premium_access(self, user_id: Optional[str]) -> bool:
        ...

    @abstractmethod
    def activate_plan(self, user_id: str, plan_id: str, payment_ref: Optional[str] = None) -> LicenseInfo:
        ...

    @abstractmethod
    def start_trial(self, user_id: str) -> LicenseInfo:
        ...


class PaymentService(ABC):
    @abstractmethod
    def create_purchase(self, user_id: str, plan_id: str) -> PurchaseResult:
        ...

    @abstractmethod
    def get_checkout(self, user_id: str, payment_id: str) -> PurchaseResult:
        ...

    @abstractmethod
    def confirm_purchase(self, user_id: str, payment_id: str) -> LicenseInfo:
        ...

    @abstractmethod
    def fail_purchase(self, user_id: str, payment_id: str) -> LicenseInfo:
        ...

    @abstractmethod
    def cancel_purchase(self, user_id: str, payment_id: str) -> LicenseInfo:
        ...
