"""End-to-end lifecycle simulation with no external services.

    python -m examples.simulate_lifecycle
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from bot.config import DEFAULT_PLANS
from bot.gateways import FakePaymentGateway, RecordingChatGateway
from bot.models import PaymentEvent
from bot.repository import (
    InMemoryMemberRepository,
    InMemoryProcessedEventRepository,
)
from bot.service import EVENT_PAYMENT_SUCCEEDED, MembershipService


def main() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    chat = RecordingChatGateway()
    service = MembershipService(
        plans=DEFAULT_PLANS,
        members=InMemoryMemberRepository(),
        processed=InMemoryProcessedEventRepository(),
        chat=chat,
        payments=FakePaymentGateway(),
    )

    print("1) User starts checkout")
    print("   ->", service.start_checkout(1001, "monthly", now))

    print("2) Stripe confirms payment (delivered twice to prove idempotency)")
    event = PaymentEvent(
        id="evt_1",
        type=EVENT_PAYMENT_SUCCEEDED,
        user_id=1001,
        plan_id="monthly",
        stripe_subscription_id="sub_1001",
        current_period_end=now + timedelta(days=30),
    )
    print("   first delivery handled:", service.process_event(event, now))
    print("   duplicate handled:", service.process_event(event, now))
    print("   granted:", chat.granted)

    print("3) 31 days later, the sweep expires the membership")
    expired = service.sweep_expired(now + timedelta(days=31))
    print("   expired:", [m.user_id for m in expired])
    print("   revoked:", chat.revoked)


if __name__ == "__main__":
    main()
