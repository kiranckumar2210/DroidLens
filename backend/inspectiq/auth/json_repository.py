"""JSON file persistence fallback when SQLite is unavailable."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from inspectiq.auth.config import get_auth_config
from inspectiq.auth.plans import get_plan
from inspectiq.auth.payment_helpers import new_order_id, new_transaction_id, overlay_pending_payment
from inspectiq.auth.models import AuthUser, LicenseInfo, LicenseStatus
from inspectiq.auth.security import hash_password, hash_refresh_token, verify_password

PENDING_STATUSES = ('created', 'pending')


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value).replace('Z', '+00:00'))


def _serialize_dt(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _compute_license(lic: dict[str, Any]) -> LicenseInfo:
    now = datetime.now(timezone.utc)
    plan = get_plan(lic.get('plan_id', 'trial')) or get_plan('trial')
    plan_name = plan.name if plan else lic.get('plan_id', 'trial')
    price_inr = plan.price_inr if plan else None

    if lic.get('status') == LicenseStatus.LIFETIME.value:
        return LicenseInfo(
            status=LicenseStatus.LIFETIME,
            plan_id=lic['plan_id'],
            plan_name=plan_name,
            trial_started_at=_parse_dt(lic.get('trial_started_at')),
            trial_expires_at=_parse_dt(lic.get('trial_expires_at')),
            license_activated_at=_parse_dt(lic.get('license_activated_at')),
            license_expires_at=None,
            days_remaining=None,
            has_premium=True,
            price_inr=price_inr,
            license_id=f"lifetime-{lic['user_id']}",
        )

    trial_expires_at = _parse_dt(lic.get('trial_expires_at'))
    if trial_expires_at:
        days_left = max(0, (trial_expires_at.date() - now.date()).days)
        if now < trial_expires_at and lic.get('status') == LicenseStatus.TRIAL_ACTIVE.value:
            return LicenseInfo(
                status=LicenseStatus.TRIAL_ACTIVE,
                plan_id='trial',
                plan_name='Free Trial',
                trial_started_at=_parse_dt(lic.get('trial_started_at')),
                trial_expires_at=trial_expires_at,
                days_remaining=days_left,
                has_premium=True,
                price_inr=None,
            )
        return LicenseInfo(
            status=LicenseStatus.TRIAL_EXPIRED,
            plan_id='trial',
            plan_name='Free Trial (Expired)',
            trial_started_at=_parse_dt(lic.get('trial_started_at')),
            trial_expires_at=trial_expires_at,
            days_remaining=0,
            has_premium=False,
            price_inr=None,
        )

    return LicenseInfo(
        status=LicenseStatus.TRIAL_EXPIRED,
        plan_id=lic.get('plan_id', 'trial'),
        plan_name=plan_name,
        has_premium=False,
    )


class JsonAuthRepository:
    """File-backed auth store used when stdlib SQLite is missing."""

    def __init__(self, db_path: Optional[str] = None):
        home = Path.home() / '.droidlens'
        home.mkdir(parents=True, exist_ok=True)
        if db_path:
            self.db_path = str(Path(db_path).with_suffix('.json'))
        else:
            self.db_path = str(home / 'auth.json')
        self._data: dict[str, Any] = {
            'users': {}, 'licenses': {}, 'payments': {}, 'refresh_tokens': {},
            'system_settings': {},
        }
        self._load()

    def _load(self) -> None:
        path = Path(self.db_path)
        if path.exists():
            self._data = json.loads(path.read_text(encoding='utf-8'))

    def _save(self) -> None:
        Path(self.db_path).write_text(json.dumps(self._data, indent=2), encoding='utf-8')

    @staticmethod
    def _to_user(row: dict[str, Any]) -> AuthUser:
        return AuthUser(
            id=row['id'],
            full_name=row['full_name'],
            email=row['email'],
            created_at=_parse_dt(row['created_at']) or datetime.now(timezone.utc),
            avatar_url=row.get('avatar_url'),
            last_login=_parse_dt(row.get('last_login')),
            status=row.get('status', 'active'),
        )

    def _registration_license(self, now: datetime) -> tuple[str, str, Optional[str], Optional[str], Optional[str]]:
        from inspectiq.auth.system_settings_service import get_system_settings_service

        settings = get_system_settings_service().get_settings()
        if not settings.subscription.subscription_enabled or not settings.subscription.trial_enabled:
            return (
                'lifetime',
                LicenseStatus.LIFETIME.value,
                None,
                None,
                _serialize_dt(now),
            )
        trial_plan = get_plan('trial')
        trial_days = settings.payment.trial_days or (trial_plan.trial_days if trial_plan else 7)
        trial_end = now + timedelta(days=trial_days)
        return (
            'trial',
            LicenseStatus.TRIAL_ACTIVE.value,
            _serialize_dt(now),
            _serialize_dt(trial_end),
            None,
        )

    def create_user(self, full_name: str, email: str, password: str) -> AuthUser:
        email_key = email.lower().strip()
        for row in self._data['users'].values():
            if row['email'] == email_key:
                raise ValueError('An account with this email already exists')

        uid = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        plan_id, status, trial_start, trial_end, activated = self._registration_license(now)

        self._data['users'][uid] = {
            'id': uid,
            'full_name': full_name.strip(),
            'email': email_key,
            'password_hash': hash_password(password),
            'avatar_url': None,
            'status': 'active',
            'last_login': None,
            'created_at': _serialize_dt(now),
            'updated_at': _serialize_dt(now),
        }
        self._data['licenses'][uid] = {
            'user_id': uid,
            'plan_id': plan_id,
            'status': status,
            'trial_started_at': trial_start,
            'trial_expires_at': trial_end,
            'license_activated_at': activated,
            'license_expires_at': None,
            'payment_ref': None,
            'updated_at': _serialize_dt(now),
        }
        self._save()
        return self._to_user(self._data['users'][uid])

    def authenticate(self, email: str, password: str) -> Optional[AuthUser]:
        email_key = email.lower().strip()
        for row in self._data['users'].values():
            if row['email'] == email_key and verify_password(password, row['password_hash']):
                row['last_login'] = _serialize_dt(datetime.now(timezone.utc))
                self._save()
                return self._to_user(row)
        return None

    def record_login(self, user_id: str) -> None:
        row = self._data['users'].get(user_id)
        if row:
            row['last_login'] = _serialize_dt(datetime.now(timezone.utc))
            self._save()

    def get_user(self, user_id: str) -> Optional[AuthUser]:
        row = self._data['users'].get(user_id)
        return self._to_user(row) if row else None

    def update_user(
        self,
        user_id: str,
        full_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> AuthUser:
        row = self._data['users'].get(user_id)
        if not row:
            raise ValueError('User not found')
        if full_name is not None:
            row['full_name'] = full_name.strip()
        if avatar_url is not None:
            row['avatar_url'] = avatar_url
        row['updated_at'] = _serialize_dt(datetime.now(timezone.utc))
        self._save()
        return self._to_user(row)

    def change_password(self, user_id: str, current: str, new_password: str) -> None:
        row = self._data['users'].get(user_id)
        if not row or not verify_password(current, row['password_hash']):
            raise ValueError('Current password is incorrect')
        row['password_hash'] = hash_password(new_password)
        row['updated_at'] = _serialize_dt(datetime.now(timezone.utc))
        self._save()

    def delete_user(self, user_id: str, password: str) -> None:
        row = self._data['users'].get(user_id)
        if not row or not verify_password(password, row['password_hash']):
            raise ValueError('Password is incorrect')
        self._data['users'].pop(user_id, None)
        self._data['licenses'].pop(user_id, None)
        self._data['payments'] = {
            pid: pay for pid, pay in self._data['payments'].items() if pay.get('user_id') != user_id
        }
        self._data['refresh_tokens'] = {
            tid: tok for tid, tok in self._data.get('refresh_tokens', {}).items()
            if tok.get('user_id') != user_id
        }
        self._save()

    def get_license(self, user_id: str) -> LicenseInfo:
        lic = self._data['licenses'].get(user_id)
        if not lic:
            raise ValueError('License not found')
        info = _compute_license(lic)
        if info.status == LicenseStatus.TRIAL_EXPIRED and lic.get('status') != LicenseStatus.TRIAL_EXPIRED.value:
            lic['status'] = LicenseStatus.TRIAL_EXPIRED.value
            self._save()
        pending = self.get_pending_payment(user_id)
        return overlay_pending_payment(info, pending)

    def get_pending_payment(self, user_id: str) -> Optional[dict]:
        pending = [
            p for p in self._data['payments'].values()
            if p.get('user_id') == user_id and p.get('status') in PENDING_STATUSES
        ]
        if not pending:
            return None
        pending.sort(key=lambda p: p.get('created_at', ''), reverse=True)
        return pending[0]

    def get_payment(self, payment_id: str, user_id: str) -> Optional[dict]:
        pay = self._data['payments'].get(payment_id)
        if not pay or pay.get('user_id') != user_id:
            return None
        return pay

    def list_user_orders(self, user_id: str) -> list[dict]:
        orders = [p for p in self._data['payments'].values() if p.get('user_id') == user_id]
        orders.sort(key=lambda p: p.get('created_at', ''), reverse=True)
        return orders

    def create_payment(
        self,
        user_id: str,
        plan_id: str,
        amount_inr: int,
        currency: str = 'INR',
        payment_provider: str = 'mock',
    ) -> dict:
        existing = self.get_pending_payment(user_id)
        if existing:
            return existing
        pid = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        payment = {
            'id': pid,
            'payment_id': pid,
            'order_id': new_order_id(),
            'transaction_id': new_transaction_id(),
            'user_id': user_id,
            'plan_id': plan_id,
            'amount_inr': amount_inr,
            'amount': amount_inr,
            'currency': currency,
            'payment_provider': payment_provider,
            'status': 'pending',
            'created_at': _serialize_dt(now),
            'completed_at': None,
        }
        self._data['payments'][pid] = payment
        self._save()
        return payment

    def complete_payment(self, payment_id: str, user_id: str) -> None:
        pay = self._data['payments'].get(payment_id)
        if not pay or pay.get('user_id') != user_id:
            raise ValueError('Payment not found')
        if pay.get('status') not in PENDING_STATUSES:
            raise ValueError(f"Payment cannot be completed (status: {pay.get('status')})")
        pay['status'] = 'completed'
        pay['completed_at'] = _serialize_dt(datetime.now(timezone.utc))
        self._save()

    def fail_payment(self, payment_id: str, user_id: str) -> None:
        pay = self._data['payments'].get(payment_id)
        if not pay or pay.get('user_id') != user_id:
            raise ValueError('Payment not found')
        if pay.get('status') not in PENDING_STATUSES:
            raise ValueError(f"Payment cannot be failed (status: {pay.get('status')})")
        pay['status'] = 'failed'
        pay['completed_at'] = _serialize_dt(datetime.now(timezone.utc))
        self._save()

    def cancel_payment(self, payment_id: str, user_id: str) -> None:
        pay = self._data['payments'].get(payment_id)
        if not pay or pay.get('user_id') != user_id:
            raise ValueError('Payment not found')
        if pay.get('status') not in PENDING_STATUSES:
            raise ValueError(f"Payment cannot be cancelled (status: {pay.get('status')})")
        pay['status'] = 'cancelled'
        pay['completed_at'] = _serialize_dt(datetime.now(timezone.utc))
        self._save()

    def refund_payment(self, payment_id: str, user_id: str) -> None:
        pay = self._data['payments'].get(payment_id)
        if not pay or pay.get('user_id') != user_id:
            raise ValueError('Payment not found')
        if pay.get('status') != 'completed':
            raise ValueError(f"Payment cannot be refunded (status: {pay.get('status')})")
        pay['status'] = 'refunded'
        pay['completed_at'] = _serialize_dt(datetime.now(timezone.utc))
        self._save()

    def store_refresh_token(self, user_id: str, jti: str, token: str, expires_at: datetime) -> None:
        if 'refresh_tokens' not in self._data:
            self._data['refresh_tokens'] = {}
        self._data['refresh_tokens'][jti] = {
            'id': jti,
            'user_id': user_id,
            'token_hash': hash_refresh_token(token),
            'expires_at': _serialize_dt(expires_at),
            'revoked': False,
        }
        self._save()

    def validate_refresh_token(self, jti: str, token: str) -> Optional[str]:
        row = self._data.get('refresh_tokens', {}).get(jti)
        if not row or row.get('revoked'):
            return None
        exp = _parse_dt(row.get('expires_at'))
        if not exp or datetime.now(timezone.utc) >= exp:
            return None
        if row.get('token_hash') != hash_refresh_token(token):
            return None
        return row['user_id']

    def revoke_refresh_token(self, jti: str) -> None:
        row = self._data.get('refresh_tokens', {}).get(jti)
        if row:
            row['revoked'] = True
            self._save()

    def revoke_all_refresh_tokens(self, user_id: str) -> None:
        for row in self._data.get('refresh_tokens', {}).values():
            if row.get('user_id') == user_id:
                row['revoked'] = True
        self._save()

    def activate_lifetime(self, user_id: str, payment_ref: Optional[str] = None) -> LicenseInfo:
        lic = self._data['licenses'].get(user_id)
        if not lic:
            raise ValueError('License not found')
        now = datetime.now(timezone.utc)
        lic.update({
            'plan_id': 'lifetime',
            'status': LicenseStatus.LIFETIME.value,
            'license_activated_at': _serialize_dt(now),
            'license_expires_at': None,
            'payment_ref': payment_ref,
            'updated_at': _serialize_dt(now),
        })
        self._save()
        return _compute_license(lic)

    def get_payment_plan_id(self, payment_id: str) -> str:
        pay = self._data['payments'].get(payment_id)
        if not pay:
            raise ValueError('Payment not found')
        return pay['plan_id']

    def get_system_settings(self) -> dict[str, Any]:
        return self._data.get('system_settings', {}).get('default', {})

    def update_system_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        if 'system_settings' not in self._data:
            self._data['system_settings'] = {}
        self._data['system_settings']['default'] = settings
        self._save()
        return settings

    def admin_set_license(self, user_id: str, license_type: str) -> LicenseInfo:
        user = self._data['users'].get(user_id)
        lic = self._data['licenses'].get(user_id)
        if not user or not lic:
            raise ValueError('User not found')
        now = datetime.now(timezone.utc)
        if license_type == 'suspended':
            user['status'] = 'suspended'
        elif license_type == 'guest':
            user['status'] = 'active'
            lic.update({
                'plan_id': 'guest',
                'status': LicenseStatus.TRIAL_EXPIRED.value,
                'trial_started_at': None,
                'trial_expires_at': None,
                'license_activated_at': None,
                'license_expires_at': None,
                'payment_ref': None,
            })
        elif license_type == 'trial':
            user['status'] = 'active'
            from inspectiq.auth.system_settings_service import get_system_settings_service
            trial_days = get_system_settings_service().get_settings().payment.trial_days
            trial_end = now + timedelta(days=trial_days)
            lic.update({
                'plan_id': 'trial',
                'status': LicenseStatus.TRIAL_ACTIVE.value,
                'trial_started_at': _serialize_dt(now),
                'trial_expires_at': _serialize_dt(trial_end),
                'license_activated_at': None,
                'license_expires_at': None,
                'payment_ref': None,
            })
        elif license_type in ('premium', 'lifetime'):
            user['status'] = 'active'
            lic.update({
                'plan_id': 'lifetime' if license_type == 'lifetime' else 'premium',
                'status': LicenseStatus.LIFETIME.value,
                'license_activated_at': _serialize_dt(now),
                'license_expires_at': None,
                'payment_ref': 'admin-grant',
            })
        elif license_type == 'expired':
            user['status'] = 'active'
            lic.update({
                'plan_id': 'trial',
                'status': LicenseStatus.TRIAL_EXPIRED.value,
                'trial_expires_at': _serialize_dt(now - timedelta(days=1)),
            })
        else:
            raise ValueError(f'Unknown license type: {license_type}')
        lic['updated_at'] = _serialize_dt(now)
        self._save()
        return _compute_license(lic)
