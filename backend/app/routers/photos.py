from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User, Photo, Subscription, SubscriptionStatus
from app.auth import get_current_user
from app.utils.s3_client import upload_photo, get_presigned_url, delete_photo
from datetime import datetime, timezone

router = APIRouter(prefix="/photos", tags=["photos"])


class PhotoListItem(BaseModel):
    id: str
    title: str
    preview_url: str
    is_locked: bool

    class Config:
        from_attributes = True


class PhotoDetail(BaseModel):
    id: str
    title: str
    full_url: str
    uploaded_at: str


def _is_admin(user: User) -> bool:
    return user.is_admin == "true"


async def _user_has_full_access(user: User, db: AsyncSession) -> bool:
    if _is_admin(user):
        return True
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.active,
            Subscription.current_period_end > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none() is not None


@router.get("", response_model=list[PhotoListItem])
async def list_photos(
    db: AsyncSession = Depends(get_db),
):
    """List all photos with preview URLs. No auth required for browsing."""
    result = await db.execute(select(Photo).order_by(Photo.uploaded_at.desc()))
    photos = result.scalars().all()

    items = []
    for photo in photos:
        items.append(
            PhotoListItem(
                id=photo.id,
                title=photo.title,
                preview_url=get_presigned_url(photo.preview_s3_key),
                is_locked=True,
            )
        )
    return items


@router.get("/gallery", response_model=list[PhotoListItem])
async def gallery(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Authenticated gallery - shows lock status based on subscription or admin."""
    has_sub = await _user_has_full_access(user, db)

    result = await db.execute(select(Photo).order_by(Photo.uploaded_at.desc()))
    photos = result.scalars().all()

    items = []
    for photo in photos:
        url = get_presigned_url(photo.s3_key if has_sub else photo.preview_s3_key)
        items.append(
            PhotoListItem(
                id=photo.id,
                title=photo.title,
                preview_url=url,
                is_locked=not has_sub,
            )
        )
    return items


@router.get("/{photo_id}/preview")
async def get_preview(photo_id: str, db: AsyncSession = Depends(get_db)):
    """Get blurred preview - no auth required."""
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return {"preview_url": get_presigned_url(photo.preview_s3_key)}


@router.get("/{photo_id}/full", response_model=PhotoDetail)
async def get_full_photo(
    photo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full resolution photo - requires active subscription or admin."""
    has_access = await _user_has_full_access(user, db)
    if not has_access:
        raise HTTPException(status_code=403, detail="Active subscription required")

    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    return PhotoDetail(
        id=photo.id,
        title=photo.title,
        full_url=get_presigned_url(photo.s3_key),
        uploaded_at=photo.uploaded_at.isoformat(),
    )


# ── Admin Endpoints ──────────────────────────────────────────────────────────

@router.post("/admin/upload", response_model=PhotoListItem)
async def upload_new_photo(
    file: UploadFile = File(...),
    title: str = Form("Untitled"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new photo (admin only)."""
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    contents = await file.read()
    s3_key, preview_key = upload_photo(contents, file.filename)

    photo = Photo(
        title=title,
        filename=file.filename,
        s3_key=s3_key,
        preview_s3_key=preview_key,
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    return PhotoListItem(
        id=photo.id,
        title=photo.title,
        preview_url=get_presigned_url(photo.preview_s3_key),
        is_locked=True,
    )


@router.delete("/admin/{photo_id}")
async def delete_photo_endpoint(
    photo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a photo (admin only)."""
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    delete_photo(photo.s3_key, photo.preview_s3_key)
    await db.delete(photo)
    await db.commit()
    return {"status": "deleted"}
