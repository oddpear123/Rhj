import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User, Subscription, SubscriptionStatus
from app.auth import get_current_user
from app.utils.stripe_client import (
    create_checkout_session,
    create_embedded_checkout_session,
    create_customer_portal_session,
    construct_webhook_event,
)
import stripe

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscription", tags=["subscription"])


class CheckoutRequest(BaseModel):
    plan: str = "1month"


class CheckoutResponse(BaseModel):
    checkout_url: str


class SubscriptionStatusResponse(BaseModel):
    is_active: bool
    status: str | None = None
    current_period_end: str | None = None


class EmbeddedCheckoutResponse(BaseModel):
    clientSecret: str


class PortalResponse(BaseModel):
    portal_url: str


@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = create_checkout_session(user.stripe_customer_id, user.email, body.plan)
    return CheckoutResponse(checkout_url=session.url)


@router.post("/create-embedded-checkout", response_model=EmbeddedCheckoutResponse)
async def create_embedded_checkout(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = create_embedded_checkout_session(user.stripe_customer_id, user.email, body.plan)
    return EmbeddedCheckoutResponse(clientSecret=session.client_secret)


@router.get("/status", response_model=SubscriptionStatusResponse)
async def subscription_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Admins always have full access
    if user.is_admin == "true":
        return SubscriptionStatusResponse(is_active=True, status="admin")

    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.status == SubscriptionStatus.active)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub = result.scalar_one_or_none()

    if not sub:
        return SubscriptionStatusResponse(is_active=False)

    period_end = sub.current_period_end
    if period_end and period_end.tzinfo is None:
        period_end = period_end.replace(tzinfo=timezone.utc)
    if period_end and period_end < datetime.now(timezone.utc):
        sub.status = SubscriptionStatus.expired
        await db.commit()
        return SubscriptionStatusResponse(is_active=False, status="expired")

    return SubscriptionStatusResponse(
        is_active=True,
        status=sub.status.value,
        current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None,
    )


@router.post("/portal", response_model=PortalResponse)
async def customer_portal(
    user: User = Depends(get_current_user),
):
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer found. Subscribe first.")
    session = create_customer_portal_session(user.stripe_customer_id)
    return PortalResponse(portal_url=session.url)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = construct_webhook_event(payload, sig_header)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail="Webhook error")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data, db)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(data, db)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data, db)
    else:
        logger.info(f"Unhandled event type: {event_type}")

    return {"status": "ok"}


async def _handle_checkout_completed(data: dict, db: AsyncSession):
    customer_id = data.get("customer")
    subscription_id = data.get("subscription")
    customer_email = data.get("customer_details", {}).get("email") or data.get("customer_email")

    if not customer_email:
        logger.error("No email in checkout session")
        return

    result = await db.execute(select(User).where(User.email == customer_email))
    user = result.scalar_one_or_none()
    if not user:
        logger.error(f"No user found for email: {customer_email}")
        return

    if customer_id and not user.stripe_customer_id:
        user.stripe_customer_id = customer_id

    stripe_sub = stripe.Subscription.retrieve(subscription_id)

    sub = Subscription(
        user_id=user.id,
        stripe_subscription_id=subscription_id,
        status=SubscriptionStatus.active,
        current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end, tz=timezone.utc),
    )
    db.add(sub)
    await db.commit()
    logger.info(f"Subscription created for user {user.email}")


async def _handle_subscription_updated(data: dict, db: AsyncSession):
    stripe_sub_id = data.get("id")
    status_str = data.get("status")

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        logger.warning(f"No subscription found for {stripe_sub_id}")
        return

    status_map = {
        "active": SubscriptionStatus.active,
        "past_due": SubscriptionStatus.past_due,
        "canceled": SubscriptionStatus.cancelled,
        "unpaid": SubscriptionStatus.expired,
    }
    sub.status = status_map.get(status_str, SubscriptionStatus.active)
    sub.current_period_end = datetime.fromtimestamp(data.get("current_period_end", 0), tz=timezone.utc)
    await db.commit()


async def _handle_subscription_deleted(data: dict, db: AsyncSession):
    stripe_sub_id = data.get("id")
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return
    sub.status = SubscriptionStatus.cancelled
    await db.commit()
