import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum, Text, CLOB
from sqlalchemy.orm import relationship
from app.database import Base
import enum


def generate_uuid():
    return str(uuid.uuid4())


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    cancelled = "cancelled"
    expired = "expired"
    past_due = "past_due"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    stripe_customer_id = Column(String(255), nullable=True, unique=True)
    is_admin = Column(String(10), default="false")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    subscriptions = relationship("Subscription", back_populates="user", lazy="selectin")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    stripe_subscription_id = Column(String(255), unique=True, nullable=False)
    status = Column(SAEnum(SubscriptionStatus, length=20), default=SubscriptionStatus.active)
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="subscriptions", lazy="selectin")


class Photo(Base):
    __tablename__ = "photos"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False, default="Untitled")
    filename = Column(String(500), nullable=False)
    s3_key = Column(String(500), nullable=False)
    preview_s3_key = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    metadata_ = Column("metadata", CLOB, nullable=True)
