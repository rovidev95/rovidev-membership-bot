"""Telegram chat gateway (optional). Uses the Bot API over HTTPS via httpx."""

from __future__ import annotations

from bot.models import Plan


class TelegramChatGateway:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            raise ImportError("Install httpx to use TelegramChatGateway") from exc
        self._httpx = httpx
        self._base = f"https://api.telegram.org/bot{bot_token}"
        self.chat_id = chat_id

    def _call(self, method: str, payload: dict) -> None:  # pragma: no cover - needs network
        with self._httpx.Client(timeout=10) as client:
            resp = client.post(f"{self._base}/{method}", json=payload)
            resp.raise_for_status()

    def grant_access(self, user_id: int, plan: Plan) -> None:  # pragma: no cover
        # Unban so a previously-kicked user can rejoin, then send an invite link.
        self._call("unbanChatMember", {
            "chat_id": self.chat_id, "user_id": user_id, "only_if_banned": True,
        })
        invite = self._create_invite()
        self.notify(user_id, f"Your access to {plan.name} is active. Join: {invite}")

    def revoke_access(self, user_id: int) -> None:  # pragma: no cover
        self._call("banChatMember", {"chat_id": self.chat_id, "user_id": user_id})

    def notify(self, user_id: int, message: str) -> None:  # pragma: no cover
        self._call("sendMessage", {"chat_id": user_id, "text": message})

    def _create_invite(self) -> str:  # pragma: no cover
        with self._httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{self._base}/createChatInviteLink",
                json={"chat_id": self.chat_id, "member_limit": 1},
            )
            resp.raise_for_status()
            return resp.json()["result"]["invite_link"]
