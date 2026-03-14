import os
import oracledb
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./rhj.db")

engine_kwargs = {"echo": False}

# Connection overrides for different environments
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("oracle") or "oracle" in DATABASE_URL:
    # Parse out wallet_location from query string and pass via connect_args
    parsed = urlparse(DATABASE_URL)
    query_params = parse_qs(parsed.query)

    # Ensure oracle+oracledb:// prefix
    if not DATABASE_URL.startswith("oracle+oracledb://"):
        if DATABASE_URL.startswith("oracle://"):
            DATABASE_URL = DATABASE_URL.replace("oracle://", "oracle+oracledb://", 1)

    # Extract wallet params and build connect_args
    wallet_location = query_params.pop("wallet_location", [None])[0]
    wallet_password = query_params.pop("wallet_password", [None])[0]
    tns_admin = os.getenv("TNS_ADMIN") or wallet_location

    connect_args = {}
    if tns_admin:
        connect_args["config_dir"] = tns_admin
        connect_args["wallet_location"] = tns_admin
    if wallet_password:
        connect_args["wallet_password"] = wallet_password

    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    # Rebuild URL without wallet query params
    remaining_query = urlencode({k: v[0] for k, v in query_params.items()})
    parsed = parsed._replace(query=remaining_query)
    DATABASE_URL = urlunparse(parsed)

engine = create_async_engine(DATABASE_URL, **engine_kwargs)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    from app.models import User, Subscription, Photo  # noqa: F401
    from app.auth import hash_password
    from sqlalchemy import select

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed the admin account if it doesn't already exist
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == "admin@rhj.com"))
        if not result.scalar_one_or_none():
            admin = User(
                email="admin@rhj.com",
                password_hash=hash_password("admin1234"),
                is_admin="true",
            )
            session.add(admin)
            await session.commit()


async def get_db():
    async with async_session() as session:
        yield session
