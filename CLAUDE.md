# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Red Hot Jugs is a subscription-based premium photo platform. Stack: FastAPI (async) + Vue 3 + Stripe + SQLite/Postgres + AWS S3.

Default admin credentials: `admin@rhj.com` / `admin1234`

## Commands

### Backend (dev)

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Local Stripe webhook forwarding (required for subscription testing):

```bash
stripe listen --forward-to localhost:8000/subscription/webhook
```

### Frontend (dev)

```bash
cd frontend
npm run dev     # dev server on :5173
npm run build   # outputs to dist/
```

### Production (Docker)

```bash
# Fill in backend/.env.production and frontend/.env.production first
docker compose up --build

# App available at http://localhost (Nginx on port 80)
# Backend health: curl http://localhost/api/health
```

## Architecture

```
frontend/src/
  api.js          # Axios instance with JWT interceptor + 401 redirect
  router.js       # Vue Router (all routes public, access enforced per-view)
  stores/auth.js  # Pinia store: user, token, subscription state
  views/          # Page components

backend/app/
  main.py         # FastAPI app, CORS, router registration, lifespan init
  database.py     # Async SQLAlchemy engine, get_db() dependency
  models.py       # User, Subscription, Photo SQLAlchemy models
  auth.py         # JWT creation/verification, get_current_user() dependency
  routers/        # auth.py, photos.py, subscription.py
  utils/
    s3_client.py  # upload_photo(), get_presigned_url(), delete_photo()
    stripe_client.py
```

## Key Design Decisions

**Storage mode**: `s3_client.py` auto-detects whether to use S3 or local disk based on `AWS_ACCESS_KEY_ID` env var. When local, photos are served via `/uploads` static mount; when S3, presigned URLs with 1-hour expiry are used.

**Photo access control**: Every photo has both a full-res key and a blurred preview key (GaussianBlur radius=20, 800px max). Unauthenticated gallery (`GET /photos`) always returns preview URLs. Authenticated gallery (`GET /photos/gallery`) returns full URLs only for users with an active subscription or `is_admin == "true"`.

**Admin flag**: Stored as a string `"true"`/`"false"` on `User.is_admin` (not a boolean). Check with `user.is_admin == "true"`.

**Subscription gating**: Active subscription requires `status == active` AND `current_period_end > now`. Both conditions must hold.

**Database**: Defaults to `sqlite+aiosqlite:///./rhj.db` (file created in `backend/`). Override with `DATABASE_URL` env var for Postgres in production (`postgresql+asyncpg://...`).

## Environment Variables

Backend (`.env` in `backend/`):
- `SECRET_KEY` — JWT signing key
- `DATABASE_URL` — defaults to SQLite
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET`, `S3_REGION` — omit all to use local storage
- `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, `STRIPE_WEBHOOK_SECRET`
- `FRONTEND_URL` — for CORS (default: `http://localhost:5173`)

Frontend (`.env` in `frontend/`):
- `VITE_API_URL` — backend base URL (default: `http://localhost:8000`)
- `VITE_STRIPE_PUBLIC_KEY`
