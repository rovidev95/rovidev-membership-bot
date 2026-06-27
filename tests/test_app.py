from fastapi.testclient import TestClient

from bot.app import create_app
from bot.config import Settings


def _client() -> TestClient:
    # Default settings -> fake payment + recording chat backends.
    return TestClient(create_app(Settings()))


def _checkout_event(user_id: int, event_id="evt_http_1") -> dict:
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_1",
                "customer": "cus_1",
                "subscription": "sub_http_1",
                "metadata": {"user_id": str(user_id), "plan_id": "monthly"},
            }
        },
    }


def test_health():
    client = _client()
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_checkout_and_webhook_flow():
    client = _client()

    checkout = client.post("/checkout", json={"user_id": 99, "plan_id": "monthly"})
    assert checkout.status_code == 200
    assert checkout.json()["checkout_url"].startswith("https://")

    # Simulate Stripe delivering the paid event.
    res = client.post("/stripe/webhook", json=_checkout_event(99))
    assert res.status_code == 200
    assert res.json() == {"received": True, "handled": True}

    member = client.get("/members/99")
    assert member.status_code == 200
    body = member.json()
    assert body["status"] == "active"
    assert body["has_access"] is True


def test_webhook_is_idempotent_over_http():
    client = _client()
    client.post("/stripe/webhook", json=_checkout_event(50, "dup_evt"))
    second = client.post("/stripe/webhook", json=_checkout_event(50, "dup_evt"))
    assert second.json() == {"received": True, "handled": False}


def test_unknown_event_is_ignored():
    client = _client()
    res = client.post(
        "/stripe/webhook",
        json={"id": "evt_x", "type": "invoice.created", "data": {"object": {}}},
    )
    assert res.json() == {"received": True, "handled": False}


def test_member_not_found():
    client = _client()
    assert client.get("/members/123456").status_code == 404
