import os
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

STRIPE_PRICE_IDS = {
    "1month": os.getenv("STRIPE_PRICE_1MONTH", os.getenv("STRIPE_PRICE_ID", "")),
    "3month": os.getenv("STRIPE_PRICE_3MONTH", ""),
}


def create_checkout_session(stripe_customer_id: str | None, email: str, plan: str = "1month"):
    price_id = STRIPE_PRICE_IDS.get(plan)
    if not price_id:
        raise ValueError(f"Unknown plan: {plan}")

    params = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": f"{FRONTEND_URL}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{FRONTEND_URL}/pricing",
    }
    if stripe_customer_id:
        params["customer"] = stripe_customer_id
    else:
        params["customer_email"] = email

    return stripe.checkout.Session.create(**params)


def create_embedded_checkout_session(stripe_customer_id: str | None, email: str, plan: str = "1month"):
    """Create an embedded checkout session that returns a client_secret for in-page rendering."""
    price_id = STRIPE_PRICE_IDS.get(plan)
    if not price_id:
        raise ValueError(f"Unknown plan: {plan}")

    params = {
        "ui_mode": "embedded",
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "return_url": f"{FRONTEND_URL}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
    }
    if stripe_customer_id:
        params["customer"] = stripe_customer_id
    else:
        params["customer_email"] = email

    return stripe.checkout.Session.create(**params)


def create_customer_portal_session(stripe_customer_id: str):
    return stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=f"{FRONTEND_URL}/dashboard",
    )


def construct_webhook_event(payload: bytes, sig_header: str):
    return stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
