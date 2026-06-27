from datetime import timedelta

from bot.models import MemberStatus, PaymentEvent
from bot.service import EVENT_PAYMENT_SUCCEEDED


def _activate(service, user_id, now, days=30):
    service.process_event(
        PaymentEvent(
            id=f"evt_{user_id}",
            type=EVENT_PAYMENT_SUCCEEDED,
            user_id=user_id,
            plan_id="monthly",
            stripe_subscription_id=f"sub_{user_id}",
            current_period_end=now + timedelta(days=days),
        ),
        now,
    )


def test_sweep_revokes_expired_members(service, chat, now):
    _activate(service, 1, now, days=30)
    _activate(service, 2, now, days=30)

    later = now + timedelta(days=31)
    expired = service.sweep_expired(later)

    assert len(expired) == 2
    assert service.members.get(1).status == MemberStatus.EXPIRED
    assert 1 in chat.revoked and 2 in chat.revoked


def test_sweep_keeps_active_members(service, chat, now):
    _activate(service, 1, now, days=30)
    soon = now + timedelta(days=10)
    expired = service.sweep_expired(soon)
    assert expired == []
    assert service.members.get(1).status == MemberStatus.ACTIVE
    assert chat.revoked == []
