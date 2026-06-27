"""Stripe adapters (optional). Requires the 'stripe' extra and API keys."""

from __future__ import annotations

from datetime import UTC, datetime

from bot.models import PaymentEvent, Plan
from bot.service import (
    EVENT_PAYMENT_SUCCEEDED,
    EVENT_SUB_DELETED,
    EVENT_SUB_UPDATED,
)

_HANDLED = {EVENT_PAYMENT_SUCCEEDED, EVENT_SUB_UPDATED, EVENT_SUB_DELETED}


class StripePaymentGateway:
    def __init__(self, secret_key: str, success_url: str, cancel_url: str) -> None:
        try:
            import stripe
        except ImportError as exc:  # pragma: no cover
            raise ImportError("Install the 'stripe' extra to use StripePaymentGateway") from exc
        self._stripe = stripe
        self._stripe.api_key = secret_key
        self.success_url = success_url
        self.cancel_url = cancel_url

    def create_checkout(self, user_id: int, plan: Plan) -> str:  # pragma: no cover - needs API
        session = self._stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            success_url=self.success_url,
            cancel_url=self.cancel_url,
            metadata={"user_id": str(user_id), "plan_id": plan.id},
            subscription_data={"metadata": {"user_id": str(user_id), "plan_id": plan.id}},
        )
        return session.url


def _epoch_to_dt(value: int | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(value, tz=UTC)


def to_payment_event(event: dict) -> PaymentEvent | None:
    """Convert a verified Stripe event (as dict) into our normalized event.

    Returns None for event types we don't handle.
    """
    event_type = event.get("type", "")
    if event_type not in _HANDLED:
        return None

    obj = event.get("data", {}).get("object", {})
    metadata = obj.get("metadata", {}) or {}
    user_id_raw = metadata.get("user_id")
    user_id = int(user_id_raw) if user_id_raw is not None else None

    return PaymentEvent(
        id=event.get("id", ""),
        type=event_type,
        user_id=user_id,
        plan_id=metadata.get("plan_id"),
        stripe_customer_id=_as_id(obj.get("customer")),
        stripe_subscription_id=_as_id(obj.get("subscription") or obj.get("id")),
        current_period_end=_epoch_to_dt(obj.get("current_period_end")),
        raw=event,
    )


def _as_id(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        got = value.get("id")
        return got if isinstance(got, str) else None
    return None
