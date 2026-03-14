# Red Hot Jugs

A creator monetization and secure gifting platform built with **FastAPI**, **Vue 3**, **Stripe**, and **Oracle Autonomous Database**.

---

## Architecture

```
┌──────────┐    HTTPS    ┌─────────────────────┐     ┌─────────────────────┐
│  Vue SPA │◄───────────►│  FastAPI Backend     │◄───►│ Oracle Autonomous DB│
│(GH Pages)│             │  (Oracle Cloud)      │     │ (Always Free ATP)   │
└──────────┘             └─────────┬───────────┘     └─────────────────────┘
                                   │
                       ┌───────────▼──────────────┐
                       │  Oracle Object Storage    │
                       └──────────────────────────┘
```

---

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your keys and Oracle DB details

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

cp .env.example .env
# Edit .env with your API URL and Stripe public key

npm run dev
```

### Docker

```bash
docker compose up --build
# App: http://localhost
```

---

## Deployment

- **Frontend** is deployed to GitHub Pages via GitHub Actions (`.github/workflows/deploy-pages.yml`).
- **Backend** runs on an OCI Compute instance with a systemd service.
- **Database** is an Oracle ATP instance provisioned via `grabOracle/` scripts.

---

## Project Structure

```
frontend/src/
  api.js              Axios instance with JWT interceptor
  router.js           Vue Router
  stores/auth.js      Pinia store: user, token, subscription state
  views/              Page components (incl. AdminPanel)

backend/app/
  main.py             FastAPI app, CORS, router registration
  database.py         Async SQLAlchemy engine
  models.py           User, Subscription, Photo models
  auth.py             JWT creation/verification
  routers/            auth, photos, subscription, admin
  utils/
    s3_client.py      Storage client (OCI / S3 / local)
    stripe_client.py  Stripe helpers
```

---

## Testing

```bash
cd backend
source venv/bin/activate
pip install pytest pytest-asyncio httpx
python -m pytest tests/ -v
```
