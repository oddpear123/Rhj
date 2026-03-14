from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User, Photo, Subscription, SubscriptionStatus
from app.auth import get_current_user
from app.utils.s3_client import get_object_bytes, _content_type
from datetime import datetime, timezone

router = APIRouter(tags=["admin"])


def _require_admin(user: User):
    if user.is_admin != "true":
        raise HTTPException(status_code=403, detail="Admin access required")


# ── Media proxy (no auth — keys are UUID-based, not guessable) ──────────────

@router.get("/media/{key:path}")
async def serve_media(key: str):
    """Stream a photo from storage. Works for OCI, S3, or local."""
    data = get_object_bytes(key)
    if data is None:
        raise HTTPException(status_code=404, detail="File not found")
    ext = "." + key.rsplit(".", 1)[-1] if "." in key else ".jpg"
    return Response(content=data, media_type=_content_type(ext))


# ── Admin endpoints ─────────────────────────────────────────────────────────

class UserListItem(BaseModel):
    id: str
    email: str
    is_admin: bool
    has_active_subscription: bool
    created_at: str

    class Config:
        from_attributes = True


class AdminStats(BaseModel):
    total_users: int
    total_photos: int
    active_subscriptions: int


@router.get("/admin/stats", response_model=AdminStats)
async def get_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    users = await db.execute(select(func.count()).select_from(User))
    photos = await db.execute(select(func.count()).select_from(Photo))
    subs = await db.execute(
        select(func.count()).select_from(Subscription).where(
            Subscription.status == SubscriptionStatus.active,
            Subscription.current_period_end > datetime.now(timezone.utc),
        )
    )
    return AdminStats(
        total_users=users.scalar() or 0,
        total_photos=photos.scalar() or 0,
        active_subscriptions=subs.scalar() or 0,
    )


@router.get("/admin/users", response_model=list[UserListItem])
async def list_users(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    items = []
    for u in users:
        has_sub = False
        for sub in u.subscriptions:
            if (
                sub.status == SubscriptionStatus.active
                and sub.current_period_end
                and sub.current_period_end > datetime.now(timezone.utc)
            ):
                has_sub = True
                break
        items.append(
            UserListItem(
                id=u.id,
                email=u.email,
                is_admin=u.is_admin == "true",
                has_active_subscription=has_sub,
                created_at=u.created_at.isoformat() if u.created_at else "",
            )
        )
    return items
