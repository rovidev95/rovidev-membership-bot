from datetime import timedelta

from bot.models import PaymentEvent
from bot.service import EVENT_PAYMENT_SUCCEEDED


def test_duplicate_event_processed_once(service, chat, now):
    event = PaymentEvent(
        id="evt_same",
        type=EVENT_PAYMENT_SUCCEEDED,
        user_id=7,
        plan_id="monthly",
        stripe_subscription_id="sub_7",
        current_period_end=now + timedelta(days=30),
    )

    first = service.process_event(event, now)
    second = service.process_event(event, now)

    assert first is True
    assert second is False
    # Access granted exactly once despite re-delivery.
    assert chat.granted.count((7, "monthly")) == 1
