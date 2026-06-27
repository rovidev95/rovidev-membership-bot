"""Persistence interfaces and an in-memory implementation.

Implement the same Protocols over SQL for persistence.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from bot.models import Member, MemberStatus


class MemberRepository(Protocol):
    def get(self, user_id: int) -> Member | None: ...
    def upsert(self, member: Member) -> Member: ...
    def by_subscription(self, subscription_id: str) -> Member | None: ...
    def active_expired_before(self, moment: datetime) -> list[Member]: ...


class ProcessedEventRepository(Protocol):
    def seen(self, event_id: str) -> bool: ...
    def mark(self, event_id: str) -> None: ...


class InMemoryMemberRepository:
    def __init__(self) -> None:
        self._members: dict[int, Member] = {}

    def get(self, user_id: int) -> Member | None:
        return self._members.get(user_id)

    def upsert(self, member: Member) -> Member:
        self._members[member.user_id] = member
        return member

    def by_subscription(self, subscription_id: str) -> Member | None:
        for m in self._members.values():
            if m.stripe_subscription_id == subscription_id:
                return m
        return None

    def active_expired_before(self, moment: datetime) -> list[Member]:
        out: list[Member] = []
        for m in self._members.values():
            if (
                m.status in (MemberStatus.ACTIVE, MemberStatus.CANCELED)
                and m.current_period_end is not None
                and m.current_period_end < moment
            ):
                out.append(m)
        return out

    def all(self) -> list[Member]:
        return list(self._members.values())


class InMemoryProcessedEventRepository:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def seen(self, event_id: str) -> bool:
        return event_id in self._seen

    def mark(self, event_id: str) -> None:
        self._seen.add(event_id)
