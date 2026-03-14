import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from app.database import init_db
from app.routers import auth, subscription, photos, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Red Hot Jugs API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://oddpear123.github.io")
EXTRA_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
ALLOWED_ORIGINS = [
    FRONTEND_URL,
    "https://oddpear123.github.io",
    "http://129.159.34.144:8000",
    "http://localhost:5173",
    "http://localhost:5174",
]
ALLOWED_ORIGINS.extend([o.strip() for o in EXTRA_ORIGINS if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(subscription.router)
app.include_router(photos.router)
app.include_router(admin.router)


# Serve uploaded files locally when S3 is not configured
uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
if uploads_dir.exists() and not os.getenv("AWS_ACCESS_KEY_ID"):
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok"}
