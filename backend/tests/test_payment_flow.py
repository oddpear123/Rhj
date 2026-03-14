"""Tests for the payment / subscription flow."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from app.models import Subscription, SubscriptionStatus, User
from sqlalchemy import select


# ---------------------------------------------------------------------------
# POST /subscription/create-checkout
# ---------------------------------------------------------------------------


class TestCreateCheckout:
    @patch("app.routers.subscription.create_checkout_session")
    async def test_returns_checkout_url(self, mock_create, client, user, auth_header):
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session/test123"
        mock_create.return_value = mock_session

        resp = await client.post(
            "/subscription/create-checkout",
            json={"plan": "1month"},
            headers=auth_header,
        )

        assert resp.status_code == 200
        assert resp.json()["checkout_url"] == "https://checkout.stripe.com/session/test123"
        mock_create.assert_called_once_with(user.stripe_customer_id, user.email, "1month")

    @patch("app.routers.subscription.create_checkout_session")
    async def test_default_plan_is_1month(self, mock_create, client, user, auth_header):
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session/abc"
        mock_create.return_value = mock_session

        resp = await client.post(
            "/subscription/create-checkout",
            json={},
            headers=auth_header,
        )

        assert resp.status_code == 200
        mock_create.assert_called_once_with(user.stripe_customer_id, user.email, "1month")

    @patch("app.routers.subscription.create_checkout_session")
    async def test_passes_existing_stripe_customer_id(
        self, mock_create, client, db, user, auth_header
    ):
        user.stripe_customer_id = "cus_existing"
        await db.commit()

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session/xyz"
        mock_create.return_value = mock_session

        await client.post(
            "/subscription/create-checkout",
            json={"plan": "1month"},
            headers=auth_header,
        )

        mock_create.assert_called_once_with("cus_existing", user.email, "1month")

    async def test_requires_auth(self, client):
        resp = await client.post("/subscription/create-checkout", json={"plan": "1month"})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /subscription/status
# ---------------------------------------------------------------------------


class TestSubscriptionStatus:
    async def test_no_subscription(self, client, user, auth_header):
        resp = await client.get("/subscription/status", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is False
        assert data["status"] is None

    async def test_active_subscription(
        self, client, user, auth_header, active_subscription
    ):
        resp = await client.get("/subscription/status", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is True
        assert data["status"] == "active"
        assert data["current_period_end"] is not None

    async def test_expired_subscription_auto_marks_expired(
        self, client, db, user, auth_header, expired_subscription
    ):
        resp = await client.get("/subscription/status", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is False
        assert data["status"] == "expired"

        # Verify the DB record was updated
        await db.refresh(expired_subscription)
        assert expired_subscription.status == SubscriptionStatus.expired

    async def test_admin_always_active(self, client, admin_user, admin_auth_header):
        resp = await client.get("/subscription/status", headers=admin_auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is True
        assert data["status"] == "admin"

    async def test_requires_auth(self, client):
        resp = await client.get("/subscription/status")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /subscription/portal
# ---------------------------------------------------------------------------


class TestCustomerPortal:
    @patch("app.routers.subscription.create_customer_portal_session")
    async def test_returns_portal_url(self, mock_portal, client, db, user, auth_header):
        user.stripe_customer_id = "cus_portal_test"
        await db.commit()

        mock_session = MagicMock()
        mock_session.url = "https://billing.stripe.com/session/test"
        mock_portal.return_value = mock_session

        resp = await client.post("/subscription/portal", headers=auth_header)

        assert resp.status_code == 200
        assert resp.json()["portal_url"] == "https://billing.stripe.com/session/test"
        mock_portal.assert_called_once_with("cus_portal_test")

    async def test_no_stripe_customer_returns_400(self, client, user, auth_header):
        resp = await client.post("/subscription/portal", headers=auth_header)
        assert resp.status_code == 400
        assert "Subscribe first" in resp.json()["detail"]

    async def test_requires_auth(self, client):
        resp = await client.post("/subscription/portal")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /subscription/webhook  —  checkout.session.completed
# ---------------------------------------------------------------------------


def _webhook_payload(event_type: str, data: dict) -> dict:
    return {
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "type": event_type,
        "data": {"object": data},
    }


class TestWebhookCheckoutCompleted:
    @patch("app.routers.subscription.stripe.Subscription.retrieve")
    @patch("app.routers.subscription.construct_webhook_event")
    async def test_creates_subscription(
        self, mock_construct, mock_retrieve, client, db, user
    ):
        event = _webhook_payload(
            "checkout.session.completed",
            {
                "customer": "cus_new_123",
                "subscription": "sub_new_456",
                "customer_details": {"email": user.email},
            },
        )
        mock_construct.return_value = event

        future_ts = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
        mock_stripe_sub = MagicMock()
        mock_stripe_sub.current_period_end = future_ts
        mock_retrieve.return_value = mock_stripe_sub

        resp = await client.post(
            "/subscription/webhook",
            content=b"raw_payload",
            headers={"stripe-signature": "sig_test"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Verify subscription was created in DB
        result = await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == "sub_new_456")
        )
        sub = result.scalar_one_or_none()
        assert sub is not None
        assert sub.user_id == user.id
        assert sub.status == SubscriptionStatus.active

        # Verify stripe_customer_id was linked to user
        await db.refresh(user)
        assert user.stripe_customer_id == "cus_new_123"

    @patch("app.routers.subscription.construct_webhook_event")
    async def test_no_email_does_not_crash(self, mock_construct, client, db, user):
        event = _webhook_payload(
            "checkout.session.completed",
            {"customer": "cus_x", "subscription": "sub_x"},
        )
        mock_construct.return_value = event

        resp = await client.post(
            "/subscription/webhook",
            content=b"raw",
            headers={"stripe-signature": "sig"},
        )

        assert resp.status_code == 200

    @patch("app.routers.subscription.construct_webhook_event")
    async def test_unknown_email_does_not_crash(self, mock_construct, client, db, user):
        event = _webhook_payload(
            "checkout.session.completed",
            {
                "customer": "cus_x",
                "subscription": "sub_x",
                "customer_details": {"email": "nobody@example.com"},
            },
        )
        mock_construct.return_value = event

        resp = await client.post(
            "/subscription/webhook",
            content=b"raw",
            headers={"stripe-signature": "sig"},
        )

        assert resp.status_code == 200

    @patch("app.routers.subscription.stripe.Subscription.retrieve")
    @patch("app.routers.subscription.construct_webhook_event")
    async def test_does_not_overwrite_existing_stripe_customer_id(
        self, mock_construct, mock_retrieve, client, db, user
    ):
        user.stripe_customer_id = "cus_original"
        await db.commit()

        event = _webhook_payload(
            "checkout.session.completed",
            {
                "customer": "cus_different",
                "subscription": "sub_keep",
                "customer_details": {"email": user.email},
            },
        )
        mock_construct.return_value = event

        mock_stripe_sub = MagicMock()
        mock_stripe_sub.current_period_end = int(
            (datetime.now(timezone.utc) + timedelta(days=30)).timestamp()
        )
        mock_retrieve.return_value = mock_stripe_sub

        await client.post(
            "/subscription/webhook",
            content=b"raw",
            headers={"stripe-signature": "sig"},
        )

        await db.refresh(user)
        assert user.stripe_customer_id == "cus_original"


# ---------------------------------------------------------------------------
# POST /subscription/webhook  —  customer.subscription.updated
# ---------------------------------------------------------------------------


class TestWebhookSubscriptionUpdated:
    @patch("app.routers.subscription.construct_webhook_event")
    async def test_updates_status_and_period(
        self, mock_construct, client, db, user, active_subscription
    ):
        new_end = int((datetime.now(timezone.utc) + timedelta(days=60)).timestamp())
        event = _webhook_payload(
            "customer.subscription.updated",
            {
                "id": active_subscription.stripe_subscription_id,
                "status": "past_due",
                "current_period_end": new_end,
            },
        )
        mock_construct.return_value = event

        resp = await client.post(
            "/subscription/webhook",
            content=b"raw",
            headers={"stripe-signature": "sig"},
        )

        assert resp.status_code == 200
        await db.refresh(active_subscription)
        assert active_subscription.status == SubscriptionStatus.past_due

    @patch("app.routers.subscription.construct_webhook_event")
    async def test_canceled_maps_to_cancelled(
        self, mock_construct, client, db, user, active_subscription
    ):
        event = _webhook_payload(
            "customer.subscription.updated",
            {
                "id": active_subscription.stripe_subscription_id,
                "status": "canceled",
                "current_period_end": int(datetime.now(timezone.utc).timestamp()),
            },
        )
        mock_construct.return_value = event

        await client.post(
            "/subscription/webhook",
            content=b"raw",
            headers={"stripe-signature": "sig"},
        )

        await db.refresh(active_subscription)
        assert active_subscription.status == SubscriptionStatus.cancelled

    @patch("app.routers.subscription.construct_webhook_event")
    async def test_unpaid_maps_to_expired(
        self, mock_construct, client, db, user, active_subscription
    ):
        event = _webhook_payload(
            "customer.subscription.updated",
            {
                "id": active_subscription.stripe_subscription_id,
                "status": "unpaid",
                "current_period_end": int(datetime.now(timezone.utc).timestamp()),
            },
        )
        mock_construct.return_value = event

        await client.post(
            "/subscription/webhook",
            content=b"raw",
            headers={"stripe-signature": "sig"},
        )

        await db.refresh(active_subscription)
        assert active_subscription.status == SubscriptionStatus.expired

    @patch("app.routers.subscription.construct_webhook_event")
    async def test_unknown_subscription_does_not_crash(
        self, mock_construct, client, db
    ):
        event = _webhook_payload(
            "customer.subscription.updated",
            {
                "id": "sub_nonexistent",
                "status": "active",
                "current_period_end": int(datetime.now(timezone.utc).timestamp()),
            },
        )
        mock_construct.return_value = event

        resp = await client.post(
            "/subscription/webhook",
            content=b"raw",
            headers={"stripe-signature": "sig"},
        )

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /subscription/webhook  —  customer.subscription.deleted
# ---------------------------------------------------------------------------


class TestWebhookSubscriptionDeleted:
    @patch("app.routers.subscription.construct_webhook_event")
    async def test_sets_status_to_cancelled(
        self, mock_construct, client, db, user, active_subscription
    ):
        event = _webhook_payload(
            "customer.subscription.deleted",
            {"id": active_subscription.stripe_subscription_id},
        )
        mock_construct.return_value = event

        resp = await client.post(
            "/subscription/webhook",
            content=b"raw",
            headers={"stripe-signature": "sig"},
        )

        assert resp.status_code == 200
        await db.refresh(active_subscription)
        assert active_subscription.status == SubscriptionStatus.cancelled

    @patch("app.routers.subscription.construct_webhook_event")
    async def test_nonexistent_subscription_returns_ok(
        self, mock_construct, client, db
    ):
        event = _webhook_payload(
            "customer.subscription.deleted",
            {"id": "sub_doesnt_exist"},
        )
        mock_construct.return_value = event

        resp = await client.post(
            "/subscription/webhook",
            content=b"raw",
            headers={"stripe-signature": "sig"},
        )

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /subscription/webhook  —  signature verification
# ---------------------------------------------------------------------------


class TestWebhookSignatureVerification:
    @patch(
        "app.routers.subscription.construct_webhook_event",
        side_effect=__import__("stripe").error.SignatureVerificationError(
            "bad sig", "sig_header"
        ),
    )
    async def test_invalid_signature_returns_400(self, mock_construct, client):
        resp = await client.post(
            "/subscription/webhook",
            content=b"raw",
            headers={"stripe-signature": "bad_sig"},
        )

        assert resp.status_code == 400
        assert "Invalid signature" in resp.json()["detail"]

    @patch("app.routers.subscription.construct_webhook_event")
    async def test_unhandled_event_returns_ok(self, mock_construct, client):
        event = _webhook_payload("some.unknown.event", {"foo": "bar"})
        mock_construct.return_value = event

        resp = await client.post(
            "/subscription/webhook",
            content=b"raw",
            headers={"stripe-signature": "sig"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Full flow: create checkout -> webhook -> status check
# ---------------------------------------------------------------------------


class TestEndToEndFlow:
    @patch("app.routers.subscription.stripe.Subscription.retrieve")
    @patch("app.routers.subscription.construct_webhook_event")
    @patch("app.routers.subscription.create_checkout_session")
    async def test_full_subscription_lifecycle(
        self,
        mock_checkout,
        mock_construct,
        mock_retrieve,
        client,
        db,
        user,
        auth_header,
    ):
        # Step 1: Create checkout session
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session/full_test"
        mock_checkout.return_value = mock_session

        resp = await client.post(
            "/subscription/create-checkout",
            json={"plan": "1month"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.json()["checkout_url"] == "https://checkout.stripe.com/session/full_test"

        # Step 2: Verify no active subscription yet
        resp = await client.get("/subscription/status", headers=auth_header)
        assert resp.json()["is_active"] is False

        # Step 3: Simulate checkout.session.completed webhook
        future_ts = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
        mock_stripe_sub = MagicMock()
        mock_stripe_sub.current_period_end = future_ts
        mock_retrieve.return_value = mock_stripe_sub

        event = _webhook_payload(
            "checkout.session.completed",
            {
                "customer": "cus_lifecycle",
                "subscription": "sub_lifecycle",
                "customer_details": {"email": user.email},
            },
        )
        mock_construct.return_value = event

        resp = await client.post(
            "/subscription/webhook",
            content=b"raw",
            headers={"stripe-signature": "sig"},
        )
        assert resp.status_code == 200

        # Step 4: Verify subscription is now active
        resp = await client.get("/subscription/status", headers=auth_header)
        data = resp.json()
        assert data["is_active"] is True
        assert data["status"] == "active"

        # Step 5: Simulate subscription deleted webhook
        event = _webhook_payload(
            "customer.subscription.deleted",
            {"id": "sub_lifecycle"},
        )
        mock_construct.return_value = event

        resp = await client.post(
            "/subscription/webhook",
            content=b"raw",
            headers={"stripe-signature": "sig"},
        )
        assert resp.status_code == 200

        # Step 6: Verify subscription is no longer active
        resp = await client.get("/subscription/status", headers=auth_header)
        assert resp.json()["is_active"] is False
