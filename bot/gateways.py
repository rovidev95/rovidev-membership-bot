"""Outbound integrations as small Protocols, with fakes for tests/examples."""

from __future__ import annotations

from typing import Protocol

from bot.models import Plan


class ChatGateway(Protocol):
    """Controls access in the community platform (Telegram, Discord, ...)."""

    def grant_access(self, user_id: int, plan: Plan) -> None: ...
    def revoke_access(self, user_id: int) -> None: ...
    def notify(self, user_id: int, message: str) -> None: ...


class PaymentGateway(Protocol):
    def create_checkout(self, user_id: int, plan: Plan) -> str: ...


class RecordingChatGateway:
    """Test/example double that records every action."""

    def __init__(self) -> None:
        self.granted: list[tuple[int, str]] = []
        self.revoked: list[int] = []
        self.messages: list[tuple[int, str]] = []

    def grant_access(self, user_id: int, plan: Plan) -> None:
        self.granted.append((user_id, plan.id))

    def revoke_access(self, user_id: int) -> None:
        self.revoked.append(user_id)

    def notify(self, user_id: int, message: str) -> None:
        self.messages.append((user_id, message))


class FakePaymentGateway:
    def create_checkout(self, user_id: int, plan: Plan) -> str:
        return f"https://checkout.test/{plan.id}?u={user_id}"
