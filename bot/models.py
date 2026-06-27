"""Domain models for the paid-community lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class MemberStatus(StrEnum):
    PENDING = "pending"      # checkout created, not paid yet
    ACTIVE = "active"        # paid, has access
    CANCELED = "canceled"    # cancellation scheduled, access until period end
    EXPIRED = "expired"      # period ended, access revoked
    REVOKED = "revoked"      # access removed immediately (refund/chargeback)


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    price_cents: int
    duration_days: int
    stripe_price_id: str
    # Optional role applied in the chat platform (e.g. a Telegram/Discord role).
    role: str | None = None


@dataclass
class Member:
    user_id: int                       # chat platform user id (e.g. Telegram id)
    plan_id: str
    status: MemberStatus = MemberStatus.PENDING
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    current_period_end: datetime | None = None
    joined_at: datetime | None = None
    updated_at: datetime | None = None

    def has_access(self, now: datetime) -> bool:
        if self.status == MemberStatus.ACTIVE:
            return True
        if self.status == MemberStatus.CANCELED and self.current_period_end:
            return now < self.current_period_end
        return False


@dataclass
class PaymentEvent:
    """Normalized payment-provider event the service knows how to act on."""

    id: str
    type: str
    user_id: int | None = None
    plan_id: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    current_period_end: datetime | None = None
    raw: dict = field(default_factory=dict)
