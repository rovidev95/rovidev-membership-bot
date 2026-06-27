# membership-bot

Automates access to a paid Telegram/Discord community based on Stripe
subscriptions. A payment grants access, a cancellation or refund removes it, and
a periodic sweep revokes access once the paid period ends.

The lifecycle logic lives in `MembershipService` and has no Stripe/Telegram
imports, so it's easy to test and reuse. Stripe and Telegram are adapters behind
small interfaces; in-memory/fake versions ship for local use and tests.

## Lifecycle

```
pending -> active -> canceled -> expired / revoked
```

- `checkout.session.completed` activates the member and grants access.
- `customer.subscription.deleted` revokes access immediately.
- the sweep expires members whose `current_period_end` has passed.

Webhooks are idempotent: each event id is recorded before processing, so a
re-delivery never grants access twice.

## Run it (no keys)

```bash
pip install -e ".[dev]"
python -m examples.simulate_lifecycle
uvicorn bot.app:app --reload
```

The fake backend accepts Stripe-shaped JSON directly:

```bash
curl -X POST localhost:8000/checkout -H 'content-type: application/json' \
  -d '{"user_id": 99, "plan_id": "monthly"}'

curl -X POST localhost:8000/stripe/webhook -H 'content-type: application/json' -d '{
  "id": "evt_1", "type": "checkout.session.completed",
  "data": {"object": {"customer":"cus_1","subscription":"sub_1",
    "metadata": {"user_id":"99","plan_id":"monthly"}}}
}'

curl localhost:8000/members/99
curl -X POST localhost:8000/admin/sweep
```

## Going live

```bash
pip install -e ".[stripe,telegram]"
export BOT_PAYMENT_BACKEND=stripe BOT_CHAT_BACKEND=telegram
export BOT_STRIPE_SECRET_KEY=sk_live_... BOT_STRIPE_WEBHOOK_SECRET=whsec_...
export BOT_TELEGRAM_BOT_TOKEN=... BOT_TELEGRAM_CHAT_ID=-100...
uvicorn bot.app:app
```

Point the Stripe webhook to `POST /stripe/webhook` (signature is verified in
stripe mode), schedule `membership-worker --interval 3600` for the sweep, and set
`user_id`/`plan_id` in the Checkout `metadata` so payments map to chat users.

## Layout

```
bot/
  models.py            domain types + lifecycle states
  repository.py        repo interfaces + in-memory impls
  gateways.py          ChatGateway / PaymentGateway + fakes
  service.py           lifecycle rules
  config.py            settings + plan catalog
  stripe_gateway.py    checkout + event normalization
  telegram_gateway.py  Telegram access control
  app.py               FastAPI endpoints
  worker.py            expiry sweep CLI
```

## Tests

```bash
pytest -q
ruff check .
```

## License

MIT
