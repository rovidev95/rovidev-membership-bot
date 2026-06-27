"""Membership lifecycle: checkout -> activate -> expire/revoke.

No Stripe/Telegram imports here so the rules stay provider-agnostic.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from bot.gateways import ChatGateway, PaymentGateway
from bot.models import Member, MemberStatus, PaymentEvent, Plan
from bot.repository import (
    MemberRepository,
    ProcessedEventRepository,
)

# Provider event types we act on (Stripe naming).
EVENT_PAYMENT_SUCCEEDED = "checkout.session.completed"
EVENT_SUB_UPDATED = "customer.subscription.updated"
EVENT_SUB_DELETED = "customer.subscription.deleted"


class MembershipService:
    def __init__(
        self,
        plans: dict[str, Plan],
        members: MemberRepository,
        processed: ProcessedEventRepository,
        chat: ChatGateway,
        payments: PaymentGateway,
    ) -> None:
        self.plans = plans
        self.members = members
        self.processed = processed
        self.chat = chat
        self.payments = payments

    def start_checkout(self, user_id: int, plan_id: str, now: datetime) -> str:
        plan = self._plan(plan_id)
        member = self.members.get(user_id) or Member(user_id=user_id, plan_id=plan_id)
        member.plan_id = plan_id
        if member.status not in (MemberStatus.ACTIVE, MemberStatus.CANCELED):
            member.status = MemberStatus.PENDING
        member.updated_at = now
        self.members.upsert(member)
        return self.payments.create_checkout(user_id, plan)

    def process_event(self, event: PaymentEvent, now: datetime) -> bool:
        """Return True if the event was processed, False if it was a duplicate."""
        if self.processed.seen(event.id):
            return False
        # Mark first: re-delivery of the same id is a no-op even if we crash after.
        self.processed.mark(event.id)

        if event.type == EVENT_PAYMENT_SUCCEEDED:
            self._activate(event, now)
        elif event.type == EVENT_SUB_UPDATED:
            self._update_subscription(event, now)
        elif event.type == EVENT_SUB_DELETED:
            self._revoke(event, now)
        return True

    def _activate(self, event: PaymentEvent, now: datetime) -> None:
        if event.user_id is None:
            raise ValueError("payment event missing user_id metadata")
        plan = self._plan(event.plan_id)

        member = self.members.get(event.user_id) or Member(
            user_id=event.user_id, plan_id=plan.id
        )
        first_time = member.joined_at is None
        member.plan_id = plan.id
        member.status = MemberStatus.ACTIVE
        member.stripe_customer_id = event.stripe_customer_id
        member.stripe_subscription_id = event.stripe_subscription_id
        member.current_period_end = event.current_period_end or (
            now + timedelta(days=plan.duration_days)
        )
        member.joined_at = member.joined_at or now
        member.updated_at = now
        self.members.upsert(member)

        self.chat.grant_access(member.user_id, plan)
        self.chat.notify(
            member.user_id,
            f"Welcome to {plan.name}! Your access is active." if first_time
            else f"Your {plan.name} access has been renewed.",
        )

    def _update_subscription(self, event: PaymentEvent, now: datetime) -> None:
        member = self._member_for_event(event)
        if member is None:
            return
        if event.current_period_end:
            member.current_period_end = event.current_period_end
            # Renewal keeps access active.
            if member.status in (MemberStatus.EXPIRED, MemberStatus.PENDING):
                member.status = MemberStatus.ACTIVE
                self.chat.grant_access(member.user_id, self._plan(member.plan_id))
        member.updated_at = now
        self.members.upsert(member)

    def _revoke(self, event: PaymentEvent, now: datetime) -> None:
        member = self._member_for_event(event)
        if member is None:
            return
        member.status = MemberStatus.REVOKED
        member.updated_at = now
        self.members.upsert(member)
        self.chat.revoke_access(member.user_id)
        self.chat.notify(member.user_id, "Your subscription ended. Access removed.")

    def sweep_expired(self, now: datetime) -> list[Member]:
        """Revoke access for members whose paid period has ended."""
        expired: list[Member] = []
        for member in self.members.active_expired_before(now):
            member.status = MemberStatus.EXPIRED
            member.updated_at = now
            self.members.upsert(member)
            self.chat.revoke_access(member.user_id)
            self.chat.notify(
                member.user_id, "Your membership expired. Renew to regain access."
            )
            expired.append(member)
        return expired

    def _plan(self, plan_id: str | None) -> Plan:
        if not plan_id or plan_id not in self.plans:
            raise ValueError(f"unknown plan: {plan_id}")
        return self.plans[plan_id]

    def _member_for_event(self, event: PaymentEvent) -> Member | None:
        if event.stripe_subscription_id:
            member = self.members.by_subscription(event.stripe_subscription_id)
            if member:
                return member
        if event.user_id is not None:
            return self.members.get(event.user_id)
        return None
