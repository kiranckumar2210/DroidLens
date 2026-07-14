"""SQLite persistence for users and licenses."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from inspectiq.auth.sqlite_compat import ensure_sqlite3

ensure_sqlite3()

from sqlalchemy import Column, DateTime, Integer, String, create_engine, func, or_, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from inspectiq.auth.config import get_auth_config
from inspectiq.auth.plans import get_plan
from inspectiq.auth.payment_helpers import new_order_id, new_transaction_id, overlay_pending_payment
from inspectiq.auth.models import AuthUser, LicenseInfo, LicenseStatus
from inspectiq.auth.security import hash_password, hash_refresh_token, verify_password

PENDING_STATUSES = ("created", "pending", "initiated", "processing")


class AuthBase(DeclarativeBase):
    pass


class UserORM(AuthBase):
    __tablename__ = "auth_users"
    id = Column(String, primary_key=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")
    role = Column(String, nullable=False, default="user", index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)


class UserLicenseORM(AuthBase):
    __tablename__ = "auth_licenses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, unique=True, index=True)
    plan_id = Column(String, nullable=False, default="trial")
    status = Column(String, nullable=False, default=LicenseStatus.TRIAL_ACTIVE.value)
    trial_started_at = Column(DateTime, nullable=True)
    trial_expires_at = Column(DateTime, nullable=True)
    license_activated_at = Column(DateTime, nullable=True)
    license_expires_at = Column(DateTime, nullable=True)
    payment_ref = Column(String, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PaymentORM(AuthBase):
    __tablename__ = "auth_payments"
    id = Column(String, primary_key=True)
    order_id = Column(String, nullable=False, index=True)
    transaction_id = Column(String, nullable=False)
    merchant_transaction_id = Column(String, nullable=True, index=True)
    phonepe_order_id = Column(String, nullable=True)
    phonepe_transaction_id = Column(String, nullable=True)
    user_id = Column(String, nullable=False, index=True)
    plan_id = Column(String, nullable=False)
    amount_inr = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, default="INR")
    payment_provider = Column(String, nullable=False, default="mock")
    payment_method = Column(String, nullable=True)
    checkout_url = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)


class WebhookEventORM(AuthBase):
    __tablename__ = "auth_webhook_events"
    id = Column(String, primary_key=True)
    payment_id = Column(String, nullable=True, index=True)
    processed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RefreshTokenORM(AuthBase):
    __tablename__ = "auth_refresh_tokens"
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    token_hash = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuditEventORM(AuthBase):
    __tablename__ = "auth_audit_events"
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True, index=True)
    user_email = Column(String, nullable=True)
    action = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="success")
    detail = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class SystemSettingsORM(AuthBase):
    __tablename__ = "system_settings"
    id = Column(String, primary_key=True, default="default")
    settings_json = Column(String, nullable=False, default="{}")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SqlAuthRepository:
    def __init__(self, db_path: Optional[str] = None):
        import os

        env_db = os.environ.get("DROIDLENS_AUTH_DB")
        if env_db:
            db_path = env_db
        if db_path:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self.db_path = db_path
        else:
            home = Path.home() / ".droidlens"
            home.mkdir(parents=True, exist_ok=True)
            self.db_path = str(home / "auth.db")
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        AuthBase.metadata.create_all(self.engine)
        self._migrate_schema()
        self.SessionLocal = sessionmaker(bind=self.engine)

    def _table_exists(self, conn, table: str) -> bool:
        row = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
            {"t": table},
        ).fetchone()
        return row is not None

    def _table_columns(self, conn, table: str) -> set[str]:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return {str(r[1]) for r in rows}

    def _ensure_columns(self, conn, table: str, columns: dict[str, str]) -> None:
        if not self._table_exists(conn, table):
            return
        existing = self._table_columns(conn, table)
        for col, coltype in columns.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}"))

    def _migrate_schema(self) -> None:
        """Add columns introduced after initial release — safe for existing auth.db files."""
        with self.engine.connect() as conn:
            self._ensure_columns(conn, "auth_users", {
                "last_login": "DATETIME",
                "status": "VARCHAR DEFAULT 'active'",
                "role": "VARCHAR DEFAULT 'user'",
            })
            self._ensure_columns(conn, "auth_payments", {
                "order_id": "VARCHAR",
                "transaction_id": "VARCHAR",
                "currency": "VARCHAR DEFAULT 'INR'",
                "payment_provider": "VARCHAR DEFAULT 'mock'",
                "completed_at": "DATETIME",
                "merchant_transaction_id": "VARCHAR",
                "phonepe_order_id": "VARCHAR",
                "phonepe_transaction_id": "VARCHAR",
                "payment_method": "VARCHAR",
                "checkout_url": "VARCHAR",
                "updated_at": "DATETIME",
            })
            if self._table_exists(conn, "auth_payments"):
                conn.execute(text(
                    "UPDATE auth_payments SET order_id = 'ORD-LEGACY-' || id "
                    "WHERE order_id IS NULL OR order_id = ''"
                ))
                conn.execute(text(
                    "UPDATE auth_payments SET transaction_id = 'TXN-LEGACY-' || id "
                    "WHERE transaction_id IS NULL OR transaction_id = ''"
                ))
            if not self._table_exists(conn, "system_settings"):
                conn.execute(text(
                    "CREATE TABLE system_settings ("
                    "id VARCHAR PRIMARY KEY, "
                    "settings_json VARCHAR NOT NULL DEFAULT '{}', "
                    "updated_at DATETIME)"
                ))
            conn.commit()

    def _session(self) -> Session:
        return self.SessionLocal()

    @staticmethod
    def _to_user(row: UserORM) -> AuthUser:
        return AuthUser(
            id=row.id,
            full_name=row.full_name,
            email=row.email,
            created_at=row.created_at,
            avatar_url=row.avatar_url,
            last_login=row.last_login,
            status=row.status or "active",
            role=row.role or "user",
        )

    def _registration_license(self, now: datetime) -> tuple[str, str, Optional[datetime], Optional[datetime], Optional[datetime]]:
        """Return plan_id, status, trial_started, trial_expires, license_activated for new users."""
        from inspectiq.auth.system_settings_service import get_system_settings_service

        settings = get_system_settings_service().get_settings()
        if not settings.subscription.subscription_enabled or not settings.subscription.trial_enabled:
            return (
                "lifetime",
                LicenseStatus.LIFETIME.value,
                None,
                None,
                now,
            )
        trial_plan = get_plan("trial")
        trial_days = settings.payment.trial_days or (trial_plan.trial_days if trial_plan else 7)
        trial_end = now + timedelta(days=trial_days)
        return (
            "trial",
            LicenseStatus.TRIAL_ACTIVE.value,
            now,
            trial_end,
            None,
        )

    def create_user(self, full_name: str, email: str, password: str) -> AuthUser:
        uid = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        cfg = get_auth_config()
        normalized_email = email.lower().strip()
        role = "admin" if normalized_email in cfg.admin_emails else "user"
        plan_id, status, trial_start, trial_end, activated = self._registration_license(now)
        with self._session() as s:
            if s.query(UserORM).filter_by(email=normalized_email).first():
                raise ValueError("An account with this email already exists")
            user = UserORM(
                id=uid,
                full_name=full_name.strip(),
                email=normalized_email,
                password_hash=hash_password(password),
                role=role,
                status="active",
                created_at=now,
                updated_at=now,
            )
            s.add(user)
            s.flush()
            lic = UserLicenseORM(
                user_id=uid,
                plan_id=plan_id,
                status=status,
                trial_started_at=trial_start,
                trial_expires_at=trial_end,
                license_activated_at=activated,
            )
            s.add(lic)
            s.commit()
            return self._to_user(user)

    def authenticate(self, email: str, password: str) -> Optional[AuthUser]:
        with self._session() as s:
            row = s.query(UserORM).filter_by(email=email.lower().strip()).first()
            if not row or not verify_password(password, row.password_hash):
                return None
            if (row.status or "active") == "suspended":
                raise ValueError("Account suspended")
            row.last_login = datetime.now(timezone.utc)
            s.commit()
            return self._to_user(row)

    def record_login(self, user_id: str) -> None:
        with self._session() as s:
            row = s.query(UserORM).filter_by(id=user_id).first()
            if row:
                row.last_login = datetime.now(timezone.utc)
                s.commit()

    def get_user(self, user_id: str) -> Optional[AuthUser]:
        with self._session() as s:
            row = s.query(UserORM).filter_by(id=user_id).first()
            return self._to_user(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[AuthUser]:
        with self._session() as s:
            row = s.query(UserORM).filter_by(email=email.lower().strip()).first()
            return self._to_user(row) if row else None

    def update_user(self, user_id: str, full_name: Optional[str] = None, avatar_url: Optional[str] = None) -> AuthUser:
        with self._session() as s:
            row = s.query(UserORM).filter_by(id=user_id).first()
            if not row:
                raise ValueError("User not found")
            if full_name is not None:
                row.full_name = full_name.strip()
            if avatar_url is not None:
                row.avatar_url = avatar_url
            row.updated_at = datetime.now(timezone.utc)
            s.commit()
            return self._to_user(row)

    def change_password(self, user_id: str, current: str, new_password: str) -> None:
        with self._session() as s:
            row = s.query(UserORM).filter_by(id=user_id).first()
            if not row or not verify_password(current, row.password_hash):
                raise ValueError("Current password is incorrect")
            row.password_hash = hash_password(new_password)
            row.updated_at = datetime.now(timezone.utc)
            s.commit()

    def delete_user(self, user_id: str, password: str) -> None:
        with self._session() as s:
            row = s.query(UserORM).filter_by(id=user_id).first()
            if not row or not verify_password(password, row.password_hash):
                raise ValueError("Password is incorrect")
            s.query(UserLicenseORM).filter_by(user_id=user_id).delete()
            s.query(PaymentORM).filter_by(user_id=user_id).delete()
            s.query(RefreshTokenORM).filter_by(user_id=user_id).delete()
            s.delete(row)
            s.commit()

    def _compute_license(self, lic: UserLicenseORM) -> LicenseInfo:
        now = datetime.now(timezone.utc)
        plan = get_plan(lic.plan_id) or get_plan("trial")
        plan_name = plan.name if plan else lic.plan_id
        price_inr = plan.price_inr if plan else None

        if lic.status == LicenseStatus.LIFETIME.value:
            return LicenseInfo(
                status=LicenseStatus.LIFETIME,
                plan_id=lic.plan_id,
                plan_name=plan_name,
                trial_started_at=lic.trial_started_at,
                trial_expires_at=lic.trial_expires_at,
                license_activated_at=lic.license_activated_at,
                license_expires_at=None,
                days_remaining=None,
                has_premium=True,
                price_inr=price_inr,
                license_id=f"lifetime-{lic.user_id}",
            )

        if lic.trial_expires_at:
            exp = lic.trial_expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            days_left = max(0, (exp.date() - now.date()).days)
            if now < exp and lic.status == LicenseStatus.TRIAL_ACTIVE.value:
                return LicenseInfo(
                    status=LicenseStatus.TRIAL_ACTIVE,
                    plan_id="trial",
                    plan_name="Free Trial",
                    trial_started_at=lic.trial_started_at,
                    trial_expires_at=lic.trial_expires_at,
                    days_remaining=days_left,
                    has_premium=True,
                    price_inr=None,
                )
            return LicenseInfo(
                status=LicenseStatus.TRIAL_EXPIRED,
                plan_id="trial",
                plan_name="Free Trial (Expired)",
                trial_started_at=lic.trial_started_at,
                trial_expires_at=lic.trial_expires_at,
                days_remaining=0,
                has_premium=False,
                price_inr=None,
            )

        return LicenseInfo(
            status=LicenseStatus.TRIAL_EXPIRED,
            plan_id=lic.plan_id,
            plan_name=plan_name,
            has_premium=False,
        )

    def get_license(self, user_id: str) -> LicenseInfo:
        with self._session() as s:
            lic = s.query(UserLicenseORM).filter_by(user_id=user_id).first()
            if not lic:
                raise ValueError("License not found")
            info = self._compute_license(lic)
            if info.status == LicenseStatus.TRIAL_EXPIRED and lic.status != LicenseStatus.TRIAL_EXPIRED.value:
                lic.status = LicenseStatus.TRIAL_EXPIRED.value
                s.commit()
            pending = self.get_pending_payment(user_id)
            return overlay_pending_payment(info, pending)

    def get_pending_payment(self, user_id: str) -> Optional[dict]:
        with self._session() as s:
            pay = (
                s.query(PaymentORM)
                .filter_by(user_id=user_id)
                .filter(PaymentORM.status.in_(PENDING_STATUSES))
                .order_by(PaymentORM.created_at.desc())
                .first()
            )
            return self._payment_to_dict(pay) if pay else None

    def get_payment(self, payment_id: str, user_id: str) -> Optional[dict]:
        with self._session() as s:
            pay = s.query(PaymentORM).filter_by(id=payment_id, user_id=user_id).first()
            return self._payment_to_dict(pay) if pay else None

    @staticmethod
    def _payment_to_dict(pay: PaymentORM) -> dict:
        cfg = get_auth_config()
        return {
            "id": pay.id,
            "payment_id": pay.id,
            "order_id": pay.order_id,
            "transaction_id": pay.transaction_id,
            "merchant_transaction_id": pay.merchant_transaction_id or pay.order_id,
            "phonepe_order_id": pay.phonepe_order_id,
            "phonepe_transaction_id": pay.phonepe_transaction_id,
            "user_id": pay.user_id,
            "plan_id": pay.plan_id,
            "amount_inr": pay.amount_inr,
            "amount": pay.amount_inr,
            "currency": pay.currency or cfg.currency,
            "payment_provider": pay.payment_provider or cfg.payment_provider,
            "payment_method": pay.payment_method,
            "checkout_url": pay.checkout_url,
            "status": pay.status,
            "created_at": pay.created_at,
            "updated_at": pay.updated_at,
            "completed_at": pay.completed_at,
        }

    def get_payment_by_merchant_order_id(self, merchant_order_id: str) -> Optional[dict]:
        with self._session() as s:
            pay = (
                s.query(PaymentORM)
                .filter(
                    (PaymentORM.order_id == merchant_order_id)
                    | (PaymentORM.merchant_transaction_id == merchant_order_id)
                )
                .first()
            )
            return self._payment_to_dict(pay) if pay else None

    def update_payment_gateway(
        self,
        payment_id: str,
        user_id: str,
        *,
        status: Optional[str] = None,
        phonepe_order_id: Optional[str] = None,
        phonepe_transaction_id: Optional[str] = None,
        merchant_transaction_id: Optional[str] = None,
        payment_method: Optional[str] = None,
        checkout_url: Optional[str] = None,
    ) -> dict:
        now = datetime.now(timezone.utc)
        with self._session() as s:
            pay = s.query(PaymentORM).filter_by(id=payment_id, user_id=user_id).first()
            if not pay:
                raise ValueError("Payment not found")
            if status is not None:
                pay.status = status
            if phonepe_order_id is not None:
                pay.phonepe_order_id = phonepe_order_id
            if phonepe_transaction_id is not None:
                pay.phonepe_transaction_id = phonepe_transaction_id
            if merchant_transaction_id is not None:
                pay.merchant_transaction_id = merchant_transaction_id
            if payment_method is not None:
                pay.payment_method = payment_method
            if checkout_url is not None:
                pay.checkout_url = checkout_url
            pay.updated_at = now
            s.commit()
            return self._payment_to_dict(pay)

    def is_webhook_processed(self, event_id: str) -> bool:
        with self._session() as s:
            return s.query(WebhookEventORM).filter_by(id=event_id).first() is not None

    def mark_webhook_processed(self, event_id: str, payment_id: Optional[str] = None) -> None:
        with self._session() as s:
            if s.query(WebhookEventORM).filter_by(id=event_id).first():
                return
            s.add(WebhookEventORM(id=event_id, payment_id=payment_id))
            s.commit()

    def list_user_orders(self, user_id: str) -> list[dict]:
        with self._session() as s:
            rows = (
                s.query(PaymentORM)
                .filter_by(user_id=user_id)
                .order_by(PaymentORM.created_at.desc())
                .all()
            )
            return [self._payment_to_dict(r) for r in rows]

    def create_payment(
        self,
        user_id: str,
        plan_id: str,
        amount_inr: int,
        currency: str = "INR",
        payment_provider: str = "mock",
    ) -> dict:
        existing = self.get_pending_payment(user_id)
        if existing:
            return existing
        pid = uuid.uuid4().hex
        order_id = new_order_id()
        txn_id = new_transaction_id()
        with self._session() as s:
            s.add(PaymentORM(
                id=pid,
                order_id=order_id,
                transaction_id=txn_id,
                user_id=user_id,
                plan_id=plan_id,
                amount_inr=amount_inr,
                currency=currency,
                payment_provider=payment_provider,
                status="pending",
            ))
            s.commit()
        return self.get_payment(pid, user_id)  # type: ignore[return-value]

    def complete_payment(
        self,
        payment_id: str,
        user_id: str,
        phonepe_transaction_id: Optional[str] = None,
        payment_method: Optional[str] = None,
    ) -> None:
        with self._session() as s:
            pay = s.query(PaymentORM).filter_by(id=payment_id, user_id=user_id).first()
            if not pay:
                raise ValueError("Payment not found")
            if pay.status not in PENDING_STATUSES and pay.status != "initiated":
                if pay.status == "completed":
                    return
                raise ValueError(f"Payment cannot be completed (status: {pay.status})")
            pay.status = "completed"
            pay.completed_at = datetime.now(timezone.utc)
            pay.updated_at = pay.completed_at
            if phonepe_transaction_id:
                pay.phonepe_transaction_id = phonepe_transaction_id
                pay.transaction_id = phonepe_transaction_id
            if payment_method:
                pay.payment_method = payment_method
            s.commit()

    def fail_payment(
        self,
        payment_id: str,
        user_id: str,
        phonepe_transaction_id: Optional[str] = None,
        payment_method: Optional[str] = None,
    ) -> None:
        with self._session() as s:
            pay = s.query(PaymentORM).filter_by(id=payment_id, user_id=user_id).first()
            if not pay:
                raise ValueError("Payment not found")
            if pay.status in ("completed", "refunded"):
                return
            if pay.status not in PENDING_STATUSES and pay.status not in ("initiated", "processing"):
                if pay.status == "failed":
                    return
                raise ValueError(f"Payment cannot be failed (status: {pay.status})")
            pay.status = "failed"
            pay.completed_at = datetime.now(timezone.utc)
            pay.updated_at = pay.completed_at
            if phonepe_transaction_id:
                pay.phonepe_transaction_id = phonepe_transaction_id
            if payment_method:
                pay.payment_method = payment_method
            s.commit()

    def cancel_payment(self, payment_id: str, user_id: str) -> None:
        with self._session() as s:
            pay = s.query(PaymentORM).filter_by(id=payment_id, user_id=user_id).first()
            if not pay:
                raise ValueError("Payment not found")
            if pay.status not in PENDING_STATUSES:
                raise ValueError(f"Payment cannot be cancelled (status: {pay.status})")
            pay.status = "cancelled"
            pay.completed_at = datetime.now(timezone.utc)
            s.commit()

    def refund_payment(self, payment_id: str, user_id: str) -> None:
        with self._session() as s:
            pay = s.query(PaymentORM).filter_by(id=payment_id, user_id=user_id).first()
            if not pay:
                raise ValueError("Payment not found")
            if pay.status != "completed":
                raise ValueError(f"Payment cannot be refunded (status: {pay.status})")
            pay.status = "refunded"
            pay.completed_at = datetime.now(timezone.utc)
            s.commit()

    def store_refresh_token(self, user_id: str, jti: str, token: str, expires_at: datetime) -> None:
        with self._session() as s:
            s.add(RefreshTokenORM(
                id=jti,
                user_id=user_id,
                token_hash=hash_refresh_token(token),
                expires_at=expires_at,
            ))
            s.commit()

    def validate_refresh_token(self, jti: str, token: str) -> Optional[str]:
        now = datetime.now(timezone.utc)
        with self._session() as s:
            row = s.query(RefreshTokenORM).filter_by(id=jti).first()
            if not row or row.revoked:
                return None
            exp = row.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now >= exp:
                return None
            if row.token_hash != hash_refresh_token(token):
                return None
            return row.user_id

    def revoke_refresh_token(self, jti: str) -> None:
        with self._session() as s:
            row = s.query(RefreshTokenORM).filter_by(id=jti).first()
            if row:
                row.revoked = 1
                s.commit()

    def revoke_all_refresh_tokens(self, user_id: str) -> None:
        with self._session() as s:
            s.query(RefreshTokenORM).filter_by(user_id=user_id).update({"revoked": 1})
            s.commit()

    def activate_lifetime(self, user_id: str, payment_ref: Optional[str] = None) -> LicenseInfo:
        now = datetime.now(timezone.utc)
        with self._session() as s:
            lic = s.query(UserLicenseORM).filter_by(user_id=user_id).first()
            if not lic:
                raise ValueError("License not found")
            lic.plan_id = "lifetime"
            lic.status = LicenseStatus.LIFETIME.value
            lic.license_activated_at = now
            lic.license_expires_at = None
            lic.payment_ref = payment_ref
            lic.updated_at = now
            s.commit()
            return self._compute_license(lic)

    def get_payment_plan_id(self, payment_id: str) -> str:
        with self._session() as s:
            pay = s.query(PaymentORM).filter_by(id=payment_id).first()
            if not pay:
                raise ValueError("Payment not found")
            return pay.plan_id

    # --- Audit events ---

    def record_audit_event(
        self,
        action: str,
        *,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        status: str = "success",
        detail: Optional[str] = None,
    ) -> str:
        event_id = uuid.uuid4().hex
        with self._session() as s:
            s.add(AuditEventORM(
                id=event_id,
                user_id=user_id,
                user_email=user_email,
                action=action,
                status=status,
                detail=detail,
            ))
            s.commit()
        return event_id

    def list_audit_events(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        with self._session() as s:
            q = s.query(AuditEventORM)
            if action:
                q = q.filter(AuditEventORM.action == action)
            if user_id:
                q = q.filter(AuditEventORM.user_id == user_id)
            total = q.count()
            rows = (
                q.order_by(AuditEventORM.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            items = [
                {
                    "id": r.id,
                    "timestamp": r.created_at,
                    "user_id": r.user_id,
                    "user_email": r.user_email,
                    "action": r.action,
                    "status": r.status,
                    "detail": r.detail,
                }
                for r in rows
            ]
            return items, total

    # --- Admin helpers ---

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _start_of_day(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    def _user_row_to_admin(self, user: UserORM, lic: Optional[UserLicenseORM], payment_status: str) -> dict:
        license_type = lic.plan_id if lic else "none"
        license_status = lic.status if lic else "none"
        trial_status = "none"
        if lic:
            if lic.status == LicenseStatus.TRIAL_ACTIVE.value:
                trial_status = "active"
            elif lic.status == LicenseStatus.TRIAL_EXPIRED.value:
                trial_status = "expired"
            elif lic.trial_expires_at:
                exp = lic.trial_expires_at
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                trial_status = "active" if self._utc_now() < exp else "expired"
        return {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role or "user",
            "registration_date": user.created_at,
            "license_type": license_type,
            "license_status": license_status,
            "trial_status": trial_status,
            "payment_status": payment_status,
            "last_login": user.last_login,
            "account_status": user.status or "active",
        }

    def _latest_payment_status(self, s: Session, user_id: str) -> str:
        pay = (
            s.query(PaymentORM)
            .filter_by(user_id=user_id)
            .order_by(PaymentORM.created_at.desc())
            .first()
        )
        return pay.status if pay else "none"

    def admin_list_users(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        license_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict], int]:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        with self._session() as s:
            q = s.query(UserORM)
            if search:
                term = f"%{search.strip().lower()}%"
                q = q.filter(or_(
                    func.lower(UserORM.email).like(term),
                    func.lower(UserORM.full_name).like(term),
                ))
            if status_filter:
                q = q.filter(UserORM.status == status_filter)
            if license_filter:
                q = q.join(UserLicenseORM, UserLicenseORM.user_id == UserORM.id)
                if license_filter == "trial_active":
                    q = q.filter(UserLicenseORM.status == LicenseStatus.TRIAL_ACTIVE.value)
                elif license_filter == "trial_expired":
                    q = q.filter(UserLicenseORM.status == LicenseStatus.TRIAL_EXPIRED.value)
                elif license_filter == "lifetime":
                    q = q.filter(UserLicenseORM.status == LicenseStatus.LIFETIME.value)
            sort_col = {
                "email": UserORM.email,
                "full_name": UserORM.full_name,
                "last_login": UserORM.last_login,
                "created_at": UserORM.created_at,
            }.get(sort_by, UserORM.created_at)
            if sort_dir == "asc":
                q = q.order_by(sort_col.asc())
            else:
                q = q.order_by(sort_col.desc())
            total = q.count()
            rows = q.offset((page - 1) * page_size).limit(page_size).all()
            items = []
            for user in rows:
                lic = s.query(UserLicenseORM).filter_by(user_id=user.id).first()
                pay_status = self._latest_payment_status(s, user.id)
                items.append(self._user_row_to_admin(user, lic, pay_status))
            return items, total

    def admin_get_recent_users(self, limit: int = 10) -> list[dict]:
        items, _ = self.admin_list_users(page=1, page_size=limit, sort_by="created_at", sort_dir="desc")
        return items

    def admin_get_user_detail(self, user_id: str) -> Optional[dict]:
        with self._session() as s:
            user = s.query(UserORM).filter_by(id=user_id).first()
            if not user:
                return None
            lic = s.query(UserLicenseORM).filter_by(user_id=user_id).first()
            pay_status = self._latest_payment_status(s, user_id)
            license_info = self._compute_license(lic) if lic else None
            orders = self.list_user_orders(user_id)
            return {
                "user": self._to_user(user),
                "license": license_info,
                "orders": orders,
                "admin_row": self._user_row_to_admin(user, lic, pay_status),
            }

    def admin_update_user(
        self,
        user_id: str,
        *,
        full_name: Optional[str] = None,
        status: Optional[str] = None,
        role: Optional[str] = None,
    ) -> AuthUser:
        with self._session() as s:
            row = s.query(UserORM).filter_by(id=user_id).first()
            if not row:
                raise ValueError("User not found")
            if full_name is not None:
                row.full_name = full_name.strip()
            if status is not None:
                row.status = status
                if status == "suspended":
                    s.query(RefreshTokenORM).filter_by(user_id=user_id).update({"revoked": 1})
            if role is not None:
                row.role = role
            row.updated_at = self._utc_now()
            s.commit()
            return self._to_user(row)

    def admin_delete_user(self, user_id: str) -> None:
        with self._session() as s:
            row = s.query(UserORM).filter_by(id=user_id).first()
            if not row:
                raise ValueError("User not found")
            s.query(UserLicenseORM).filter_by(user_id=user_id).delete()
            s.query(PaymentORM).filter_by(user_id=user_id).delete()
            s.query(RefreshTokenORM).filter_by(user_id=user_id).delete()
            s.delete(row)
            s.commit()

    def admin_reset_trial(self, user_id: str) -> LicenseInfo:
        now = self._utc_now()
        trial_plan = get_plan("trial")
        trial_days = trial_plan.trial_days if trial_plan else 7
        trial_end = now + timedelta(days=trial_days)
        with self._session() as s:
            lic = s.query(UserLicenseORM).filter_by(user_id=user_id).first()
            if not lic:
                raise ValueError("License not found")
            lic.plan_id = "trial"
            lic.status = LicenseStatus.TRIAL_ACTIVE.value
            lic.trial_started_at = now
            lic.trial_expires_at = trial_end
            lic.license_activated_at = None
            lic.license_expires_at = None
            lic.payment_ref = None
            lic.updated_at = now
            s.commit()
            return self._compute_license(lic)

    def admin_suspend_user(self, user_id: str) -> AuthUser:
        return self.admin_update_user(user_id, status="suspended")

    def admin_list_payments(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict], int]:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        with self._session() as s:
            q = s.query(PaymentORM, UserORM).join(UserORM, UserORM.id == PaymentORM.user_id)
            if search:
                term = f"%{search.strip().lower()}%"
                q = q.filter(or_(
                    func.lower(UserORM.email).like(term),
                    func.lower(UserORM.full_name).like(term),
                    func.lower(PaymentORM.order_id).like(term),
                ))
            if status_filter:
                q = q.filter(PaymentORM.status == status_filter)
            sort_col = {
                "amount_inr": PaymentORM.amount_inr,
                "status": PaymentORM.status,
                "created_at": PaymentORM.created_at,
            }.get(sort_by, PaymentORM.created_at)
            if sort_dir == "asc":
                q = q.order_by(sort_col.asc())
            else:
                q = q.order_by(sort_col.desc())
            total = q.count()
            rows = q.offset((page - 1) * page_size).limit(page_size).all()
            items = []
            for pay, user in rows:
                items.append({
                    "id": pay.id,
                    "order_id": pay.order_id,
                    "transaction_id": pay.transaction_id,
                    "user_id": pay.user_id,
                    "user_name": user.full_name,
                    "user_email": user.email,
                    "amount_inr": pay.amount_inr,
                    "currency": pay.currency or "INR",
                    "payment_provider": pay.payment_provider or "mock",
                    "payment_method": pay.payment_method,
                    "status": pay.status,
                    "plan_id": pay.plan_id,
                    "created_at": pay.created_at,
                    "completed_at": pay.completed_at,
                })
            return items, total

    def admin_get_recent_payments(self, limit: int = 10) -> list[dict]:
        items, _ = self.admin_list_payments(page=1, page_size=limit)
        return items

    def count_active_sessions(self) -> int:
        now = self._utc_now()
        with self._session() as s:
            rows = s.query(RefreshTokenORM).filter(RefreshTokenORM.revoked == 0).all()
            count = 0
            for row in rows:
                exp = row.expires_at
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if now < exp:
                    count += 1
            return count

    def count_guest_sessions_today(self) -> int:
        start = self._start_of_day(self._utc_now())
        with self._session() as s:
            return (
                s.query(AuditEventORM)
                .filter(AuditEventORM.action.in_(("guest_login", "guest_session")))
                .filter(AuditEventORM.created_at >= start)
                .count()
            )

    def admin_get_kpis(self) -> dict:
        now = self._utc_now()
        start_today = self._start_of_day(now)
        with self._session() as s:
            total_users = s.query(UserORM).count()
            active_trial = s.query(UserLicenseORM).filter(
                UserLicenseORM.status == LicenseStatus.TRIAL_ACTIVE.value
            ).count()
            lifetime = s.query(UserLicenseORM).filter(
                UserLicenseORM.status == LicenseStatus.LIFETIME.value
            ).count()
            revenue_row = (
                s.query(func.coalesce(func.sum(PaymentORM.amount_inr), 0))
                .filter(PaymentORM.status == "completed")
                .scalar()
            )
            total_revenue = int(revenue_row or 0)
            payments_today = (
                s.query(PaymentORM)
                .filter(PaymentORM.created_at >= start_today)
                .count()
            )
            conversion = (lifetime / total_users * 100.0) if total_users else 0.0
            return {
                "total_registered_users": total_users,
                "active_trial_users": active_trial,
                "lifetime_subscribers": lifetime,
                "guest_sessions_today": self.count_guest_sessions_today(),
                "total_revenue_inr": total_revenue,
                "trial_conversion_rate": round(conversion, 2),
                "payments_today": payments_today,
                "active_sessions": self.count_active_sessions(),
            }

    def admin_registration_stats(self, period: str = "30d") -> dict:
        now = self._utc_now()
        start_today = self._start_of_day(now)
        start_yesterday = start_today - timedelta(days=1)
        start_week = start_today - timedelta(days=now.weekday())
        start_month = start_today.replace(day=1)
        days = 30 if period == "30d" else 7
        start_period = start_today - timedelta(days=days - 1)
        with self._session() as s:
            total = s.query(UserORM).count()
            today = s.query(UserORM).filter(UserORM.created_at >= start_today).count()
            yesterday = s.query(UserORM).filter(
                UserORM.created_at >= start_yesterday,
                UserORM.created_at < start_today,
            ).count()
            this_week = s.query(UserORM).filter(UserORM.created_at >= start_week).count()
            this_month = s.query(UserORM).filter(UserORM.created_at >= start_month).count()
            rows = (
                s.query(func.date(UserORM.created_at).label("day"), func.count(UserORM.id))
                .filter(UserORM.created_at >= start_period)
                .group_by(func.date(UserORM.created_at))
                .order_by(func.date(UserORM.created_at))
                .all()
            )
            daily = [{"date": str(day), "count": cnt} for day, cnt in rows]
            return {
                "today": today,
                "yesterday": yesterday,
                "this_week": this_week,
                "this_month": this_month,
                "total": total,
                "period": period,
                "daily": daily,
            }

    def admin_revenue_stats(self, period: str = "30d") -> dict:
        now = self._utc_now()
        start_today = self._start_of_day(now)
        start_week = start_today - timedelta(days=now.weekday())
        start_month = start_today.replace(day=1)
        with self._session() as s:
            def sum_completed(since: Optional[datetime] = None) -> int:
                q = s.query(func.coalesce(func.sum(PaymentORM.amount_inr), 0)).filter(
                    PaymentORM.status == "completed"
                )
                if since:
                    q = q.filter(PaymentORM.completed_at >= since)
                return int(q.scalar() or 0)

            total_inr = sum_completed()
            today_inr = sum_completed(start_today)
            week_inr = sum_completed(start_week)
            month_inr = sum_completed(start_month)
            user_count = s.query(UserORM).count()
            arpu = (total_inr / user_count) if user_count else 0.0
            return {
                "today_inr": today_inr,
                "week_inr": week_inr,
                "month_inr": month_inr,
                "total_inr": total_inr,
                "arpu_inr": round(arpu, 2),
                "period": period,
            }

    def admin_payment_stats(self) -> dict:
        with self._session() as s:
            total = s.query(PaymentORM).count()
            successful = s.query(PaymentORM).filter(PaymentORM.status == "completed").count()
            failed = s.query(PaymentORM).filter(PaymentORM.status == "failed").count()
            pending = s.query(PaymentORM).filter(PaymentORM.status.in_(PENDING_STATUSES)).count()
            refunded = s.query(PaymentORM).filter(PaymentORM.status == "refunded").count()
            success_rate = (successful / total * 100.0) if total else 0.0
            return {
                "total_orders": total,
                "successful": successful,
                "failed": failed,
                "pending": pending,
                "refunded": refunded,
                "success_rate": round(success_rate, 2),
            }

    def admin_subscription_stats(self) -> dict:
        with self._session() as s:
            trial_active = s.query(UserLicenseORM).filter(
                UserLicenseORM.status == LicenseStatus.TRIAL_ACTIVE.value
            ).count()
            trial_expired = s.query(UserLicenseORM).filter(
                UserLicenseORM.status == LicenseStatus.TRIAL_EXPIRED.value
            ).count()
            lifetime = s.query(UserLicenseORM).filter(
                UserLicenseORM.status == LicenseStatus.LIFETIME.value
            ).count()
            total = s.query(UserORM).count()
            conversion = (lifetime / total * 100.0) if total else 0.0
            return {
                "trial_active": trial_active,
                "trial_expired": trial_expired,
                "lifetime_users": lifetime,
                "conversion_rate": round(conversion, 2),
            }

    def admin_count_users(self) -> int:
        with self._session() as s:
            return s.query(UserORM).count()

    # --- System settings ---

    def get_system_settings(self) -> dict[str, Any]:
        with self._session() as s:
            row = s.query(SystemSettingsORM).filter_by(id="default").first()
            if not row or not row.settings_json:
                return {}
            try:
                return json.loads(row.settings_json)
            except json.JSONDecodeError:
                return {}

    def update_system_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        with self._session() as s:
            row = s.query(SystemSettingsORM).filter_by(id="default").first()
            payload = json.dumps(settings)
            if row:
                row.settings_json = payload
                row.updated_at = now
            else:
                s.add(SystemSettingsORM(id="default", settings_json=payload, updated_at=now))
            s.commit()
        return settings

    def admin_set_license(self, user_id: str, license_type: str) -> LicenseInfo:
        now = self._utc_now()
        with self._session() as s:
            user = s.query(UserORM).filter_by(id=user_id).first()
            if not user:
                raise ValueError("User not found")
            lic = s.query(UserLicenseORM).filter_by(user_id=user_id).first()
            if not lic:
                raise ValueError("License not found")

            if license_type == "suspended":
                user.status = "suspended"
                lic.updated_at = now
            elif license_type == "guest":
                user.status = "active"
                lic.plan_id = "guest"
                lic.status = LicenseStatus.TRIAL_EXPIRED.value
                lic.trial_started_at = None
                lic.trial_expires_at = None
                lic.license_activated_at = None
                lic.license_expires_at = None
                lic.payment_ref = None
                lic.updated_at = now
            elif license_type == "trial":
                user.status = "active"
                from inspectiq.auth.system_settings_service import get_system_settings_service
                trial_days = get_system_settings_service().get_settings().payment.trial_days
                trial_end = now + timedelta(days=trial_days)
                lic.plan_id = "trial"
                lic.status = LicenseStatus.TRIAL_ACTIVE.value
                lic.trial_started_at = now
                lic.trial_expires_at = trial_end
                lic.license_activated_at = None
                lic.license_expires_at = None
                lic.payment_ref = None
                lic.updated_at = now
            elif license_type in ("premium", "lifetime"):
                user.status = "active"
                lic.plan_id = "lifetime" if license_type == "lifetime" else "premium"
                lic.status = LicenseStatus.LIFETIME.value
                lic.license_activated_at = now
                lic.license_expires_at = None
                lic.payment_ref = "admin-grant"
                lic.updated_at = now
            elif license_type == "expired":
                user.status = "active"
                lic.plan_id = "trial"
                lic.status = LicenseStatus.TRIAL_EXPIRED.value
                lic.trial_expires_at = now - timedelta(days=1)
                lic.updated_at = now
            else:
                raise ValueError(f"Unknown license type: {license_type}")

            s.commit()
            return self._compute_license(lic)
