from datetime import timedelta

from bot.models import MemberStatus, PaymentEvent
from bot.service import EVENT_PAYMENT_SUCCEEDED


def _payment(user_id: int, now, event_id="evt_1") -> PaymentEvent:
    return PaymentEvent(
        id=event_id,
        type=EVENT_PAYMENT_SUCCEEDED,
        user_id=user_id,
        plan_id="monthly",
        stripe_customer_id="cus_1",
        stripe_subscription_id="sub_1",
        current_period_end=now + timedelta(days=30),
    )


def test_start_checkout_creates_pending_member(service, now):
    url = service.start_checkout(42, "monthly", now)
    assert url.startswith("https://checkout.test/")
    member = service.members.get(42)
    assert member is not None
    assert member.status == MemberStatus.PENDING


def test_start_checkout_unknown_plan(service, now):
    import pytest

    with pytest.raises(ValueError):
        service.start_checkout(42, "does-not-exist", now)


def test_payment_activates_and_grants_access(service, chat, now):
    service.process_event(_payment(42, now), now)
    member = service.members.get(42)
    assert member.status == MemberStatus.ACTIVE
    assert member.has_access(now) is True
    assert (42, "monthly") in chat.granted
    assert any("Welcome" in msg for _, msg in chat.messages)


def test_renewal_message_differs_from_welcome(service, chat, now):
    service.process_event(_payment(42, now, "evt_1"), now)
    service.process_event(_payment(42, now, "evt_2"), now)
    assert any("renewed" in msg for _, msg in chat.messages)


def test_subscription_deleted_revokes(service, chat, now):
    service.process_event(_payment(42, now), now)
    deleted = PaymentEvent(
        id="evt_del",
        type="customer.subscription.deleted",
        stripe_subscription_id="sub_1",
    )
    service.process_event(deleted, now)
    member = service.members.get(42)
    assert member.status == MemberStatus.REVOKED
    assert 42 in chat.revoked
