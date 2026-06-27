"""Configuration and plan catalog."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from bot.models import Plan

# Default plan catalog. In production load this from your DB or env.
DEFAULT_PLANS: dict[str, Plan] = {
    "monthly": Plan(
        id="monthly",
        name="Monthly membership",
        price_cents=1500,
        duration_days=30,
        stripe_price_id="price_monthly",
        role="member",
    ),
    "yearly": Plan(
        id="yearly",
        name="Yearly membership",
        price_cents=12000,
        duration_days=365,
        stripe_price_id="price_yearly",
        role="member_plus",
    ),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BOT_", env_file=".env", extra="ignore")

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    public_url: str = "http://localhost:8000"
    # "fake" (default) or "stripe"/"telegram" for real integrations.
    payment_backend: str = "fake"
    chat_backend: str = "fake"
