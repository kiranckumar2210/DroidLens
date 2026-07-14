"""Configurable licensing plans — extend without architectural changes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from inspectiq.auth.config import get_auth_config


@dataclass(frozen=True)
class PlanDefinition:
    id: str
    name: str
    description: str
    price_inr: Optional[int]  # None = free trial
    billing_period: str  # trial | lifetime | monthly | yearly | enterprise
    trial_days: int = 0
    features: List[str] = field(default_factory=lambda: ["premium"])
    active: bool = True
    sort_order: int = 0


def _build_registry() -> Dict[str, PlanDefinition]:
    cfg = get_auth_config()
    return {
        "guest": PlanDefinition(
            id="guest",
            name="Guest",
            description="Mock demo and documentation only",
            price_inr=None,
            billing_period="guest",
            features=["mock_demo", "settings", "documentation"],
            sort_order=0,
        ),
        "trial": PlanDefinition(
            id="trial",
            name="Free Trial",
            description=f"{cfg.trial_days}-day full access to all premium features",
            price_inr=None,
            billing_period="trial",
            trial_days=cfg.trial_days,
            features=["premium"],
            sort_order=1,
        ),
        "lifetime": PlanDefinition(
            id="lifetime",
            name="Lifetime License",
            description="One-time purchase — lifetime access to all current premium features",
            price_inr=cfg.lifetime_price_inr,
            billing_period="lifetime",
            features=["premium"],
            sort_order=2,
        ),
    }


def get_plan_registry() -> Dict[str, PlanDefinition]:
    return _build_registry()


def get_plan(plan_id: str) -> Optional[PlanDefinition]:
    return get_plan_registry().get(plan_id)


def list_purchasable_plans() -> List[PlanDefinition]:
    registry = get_plan_registry()
    return sorted(
        [p for p in registry.values() if p.active and p.price_inr is not None],
        key=lambda p: p.sort_order,
    )

def get_plans_sorted() -> List[PlanDefinition]:
    return sorted(get_plan_registry().values(), key=lambda p: p.sort_order)
