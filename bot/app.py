"""FastAPI surface: checkout, Stripe webhook, admin sweep, member status."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from bot.config import DEFAULT_PLANS, Settings
from bot.gateways import FakePaymentGateway, RecordingChatGateway
from bot.repository import (
    InMemoryMemberRepository,
    InMemoryProcessedEventRepository,
)
from bot.service import MembershipService
from bot.stripe_gateway import to_payment_event


class CheckoutRequest(BaseModel):
    user_id: int
    plan_id: str


def build_service(settings: Settings) -> MembershipService:
    members = InMemoryMemberRepository()
    processed = InMemoryProcessedEventRepository()

    if settings.chat_backend == "telegram":
        from bot.telegram_gateway import TelegramChatGateway

        chat = TelegramChatGateway(settings.telegram_bot_token, settings.telegram_chat_id)
    else:
        chat = RecordingChatGateway()

    if settings.payment_backend == "stripe":
        from bot.stripe_gateway import StripePaymentGateway

        payments = StripePaymentGateway(
            settings.stripe_secret_key,
            success_url=f"{settings.public_url}/success",
            cancel_url=f"{settings.public_url}/cancel",
        )
    else:
        payments = FakePaymentGateway()

    return MembershipService(DEFAULT_PLANS, members, processed, chat, payments)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="RoviDev Membership Bot",
        description="Automated paid-community access with Stripe + Telegram. By RoviDev.",
        version="1.0.0",
    )
    app.state.settings = settings
    app.state.service = build_service(settings)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "payment_backend": settings.payment_backend}

    @app.post("/checkout")
    def checkout(req: CheckoutRequest) -> dict[str, str]:
        try:
            url = app.state.service.start_checkout(
                req.user_id, req.plan_id, _now()
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"checkout_url": url}

    @app.post("/stripe/webhook")
    async def stripe_webhook(request: Request) -> dict[str, bool]:
        payload = await request.body()
        signature = request.headers.get("stripe-signature", "")
        event_dict = _verify_and_parse(settings, payload, signature)

        payment_event = to_payment_event(event_dict)
        if payment_event is None:
            return {"received": True, "handled": False}

        processed = app.state.service.process_event(payment_event, _now())
        return {"received": True, "handled": processed}

    @app.post("/admin/sweep")
    def sweep() -> dict[str, int]:
        expired = app.state.service.sweep_expired(_now())
        return {"expired": len(expired)}

    @app.get("/members/{user_id}")
    def member(user_id: int) -> dict:
        m = app.state.service.members.get(user_id)
        if not m:
            raise HTTPException(status_code=404, detail="member not found")
        return {
            "user_id": m.user_id,
            "plan_id": m.plan_id,
            "status": m.status.value,
            "has_access": m.has_access(_now()),
            "current_period_end": (
                m.current_period_end.isoformat() if m.current_period_end else None
            ),
        }

    return app


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _verify_and_parse(settings: Settings, payload: bytes, signature: str) -> dict:
    """In stripe mode, cryptographically verify the signature. Otherwise (fake
    mode for local/dev/testing) accept the JSON body as-is."""
    stripe_mode = settings.payment_backend == "stripe" and settings.stripe_webhook_secret
    if stripe_mode:  # pragma: no cover - needs API + signature
        import stripe

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.stripe_webhook_secret
            )
        except Exception as exc:  # noqa: BLE001 - surface as 400
            raise HTTPException(status_code=400, detail="invalid signature") from exc
        # stripe.Event is a dict subclass, usable directly by to_payment_event.
        return dict(event)

    import json

    try:
        return json.loads(payload.decode("utf-8"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid JSON") from exc


app = create_app()
