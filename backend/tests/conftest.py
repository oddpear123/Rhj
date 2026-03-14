import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_fake")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_fake")
os.environ.setdefault("STRIPE_PRICE_ID", "price_test_123")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.models import User, Subscription, SubscriptionStatus
from app.auth import hash_password, create_access_token
from app.main import app

engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def user(db):
    u = User(
        id=str(uuid.uuid4()),
        email="testuser@example.com",
        password_hash=hash_password("password123"),
        is_admin="false",
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest.fixture
async def admin_user(db):
    u = User(
        id=str(uuid.uuid4()),
        email="admin@rhj.com",
        password_hash=hash_password("admin1234"),
        is_admin="true",
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest.fixture
def auth_header(user):
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_header(admin_user):
    token = create_access_token(admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def active_subscription(db, user):
    sub = Subscription(
        id=str(uuid.uuid4()),
        user_id=user.id,
        stripe_subscription_id="sub_test_active",
        status=SubscriptionStatus.active,
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


@pytest.fixture
async def expired_subscription(db, user):
    sub = Subscription(
        id=str(uuid.uuid4()),
        user_id=user.id,
        stripe_subscription_id="sub_test_expired",
        status=SubscriptionStatus.active,
        current_period_end=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub
