# Red Hot Jugs

A hybrid creator monetization and secure gifting platform built with **FastAPI**, **Vue 3**, **Stripe**, and **Oracle Autonomous Database**.

---

## Technical Stack

| Layer | Technology | Host |
|---|---|---|
| Frontend | Vue 3 + Vite + Pinia | Served via Nginx (Oracle Cloud A1) |
| Backend API | FastAPI (async) + Gunicorn/Uvicorn | Oracle Cloud ARM (Always Free) |
| Database | Oracle Autonomous Database (ATP) | Oracle Cloud (Always Free) |
| Payments | Stripe Connect / Billing / Elements | Stripe |
| Object Storage | Oracle Object Storage (media proxy) | Oracle Cloud (Always Free) |
| Background Workers | Celery + Redis | Oracle Cloud ARM |
| Containerization | Docker + Docker Compose | All environments |

---

## Architecture

```
                         ┌─────────────────────┐
                         │   Stripe (Payments)  │
                         │  Connect · Billing   │
                         │  Elements · Radar    │
                         └─────────┬───────────┘
                                   │
┌──────────┐    HTTPS    ┌─────────▼───────────┐     ┌─────────────────────┐
│  Vue SPA │◄───────────►│  FastAPI Backend     │◄───►│ Oracle Autonomous DB│
│(GH Pages)│             │  (Oracle Cloud ARM)  │     │ (Always Free ATP)   │
└──────────┘             └─────────┬───────────┘     └─────────────────────┘
                                   │
                       ┌───────────▼──────────────┐
                       │  Oracle Object Storage    │
                       │  (media proxy via backend)│
                       └──────────────────────────┘
```

**Auth flow**: Register/Login → JWT → Bearer token on all API requests
**Payment flow**: Checkout Session → Stripe hosted page → Webhook confirms → Subscription active
**Photo access**: Backend media proxy streams photos from Oracle Object Storage; full-res access gated to active subscribers and admins
**Gifting flow**: Fan pays Platform → Platform purchases item → Retailer ships to Creator (address fully masked)

---

## Database — Oracle Autonomous Database (ADB)

The primary database is an **Oracle Autonomous Transaction Processing (ATP)** instance running on Oracle Cloud's Always Free tier.

- **Self-Managing**: Automatic indexing, patching, and tuning.
- **High Availability**: Built-in redundancy and automated backups.
- **Secure**: Data is encrypted at rest and in transit via Mutual TLS (mTLS) with an Oracle Wallet.
- **Connection**: The backend connects using the `oracle+oracledb` SQLAlchemy dialect with the `python-oracledb` driver in Thin mode.

### Database Setup & Provisioning

1. **Provisioning**: The database is provisioned via OCI CLI/SDK (see `grabOracle/` scripts).
2. **Connectivity**: Managed via an Oracle Wallet located in `backend/wallet/`.
3. **Environment**: `DATABASE_URL` is configured to use the `brooksdb_low` service name with the `wallet_location` parameter.

---

## Compute & Backend — Oracle Cloud Free Tier

The backend and frontend run on **Oracle Cloud Always Free Tier** ARM Ampere A1 Compute instances (up to 4 OCPUs / 24 GB RAM free).

### What runs on Oracle Cloud

- **FastAPI API server** — Gunicorn with Uvicorn async workers
- **Nginx** — Reverse proxy and static file server for the Vue SPA
- **Celery background workers** — Async task processing (subscription lifecycle, notifications, media processing)
- **Redis** — Celery broker and result backend

### Containerization

All services are containerized with Docker to ensure full parity between local development and production.

```bash
# Local development
docker compose up --build

# Production on Oracle Cloud
# The grabOracle/cloud-init.sh script handles Docker installation and setup.
```

### Reverse Proxy

Nginx handles TLS termination, static file serving, and proxies `/api/*` requests to the backend on `127.0.0.1:8000`.

---

## Payment Processing — Stripe

Stripe is the primary payment processor, selected for its comprehensive API and built-in compliance tooling.

### Stripe Products in Use

| Product | Purpose |
|---|---|
| **Stripe Connect** (Custom/Express) | Creator payouts, KYC verification, payment splitting for crowdfunded wishlist items |
| **Stripe Billing** | Recurring subscription tier management (monthly/annual) |
| **Stripe Elements** | Secure, customized checkout UI components embedded in the Vue frontend |
| **Stripe Radar** | Built-in fraud detection, chargeback protection, and risk scoring |

### Webhook Events

The backend listens for the following Stripe webhook events at `/api/subscription/webhook`:

- `checkout.session.completed` — Activate new subscription
- `customer.subscription.updated` — Handle plan changes, renewals
- `customer.subscription.deleted` — Deactivate access

### Local Development

```bash
# Forward Stripe test webhooks to the local backend
stripe listen --forward-to localhost:8000/subscription/webhook
```

---

## Frontend — GitHub Pages

The Vue 3 SPA is hosted on **GitHub Pages** at `https://brooksroley.github.io/RHJ/`.

- **Build**: `cd frontend && npm run build` outputs static files to `dist/`.
- **Deployment**: Push `dist/` to the `gh-pages` branch (manual or via CI).
- **API connection**: The frontend talks to the backend via `VITE_API_URL`. In production this points to the Oracle Cloud backend (e.g. `https://your-backend.example.com`). In development it defaults to `http://localhost:8000`.
- **CORS**: The backend allows `https://brooksroley.github.io` as an origin (configured in `ALLOWED_ORIGINS`).

### Admin Panel

The Admin Panel is available at `/admin` and is only visible to users with admin privileges.

**How to access:**
1. Log in with the admin account (`admin@rhj.com` / `admin1234`).
2. The **Admin** link appears in the navbar (red text, between Dashboard and Logout).
3. Click it to open the Admin Panel at `/admin`.

**What it includes:**
- **Stats overview** — Total users, uploaded photos, and active subscriptions at a glance.
- **Photos tab** — Grid of all uploaded photos with thumbnails. Delete any photo with a confirmation dialog.
- **Users tab** — Table of all registered users showing email, role (Admin/User), subscription status (Active/None), and join date.
- **Upload button** — Links to the photo uploader at `/admin/upload`.

All admin endpoints (`/admin/stats`, `/admin/users`) and photo management endpoints (`POST /photos/admin/upload`, `DELETE /photos/admin/{photo_id}`) require an authenticated admin user. Non-admins see a 403 page.

---

## Product Phases

### Phase 1: Security & Compliance

- **Age Verification (KYC)**: Third-party verification for creators and users via Stripe Connect identity checks.
- **High-Risk Payment Processing**: Stripe with Radar for fraud detection and chargeback mitigation.
- **Legal Compliance**: DMCA takedown procedures, 2257 record-keeping (where applicable), explicit Terms of Service.

### Phase 2: Gifting Engine

- **Address Masking**: Creator addresses are never exposed to buyers, packing slips, or tracking notifications.
- **Order Fulfillment**: Fan pays Platform → Platform purchases from retailer → Retailer ships to Creator.
- **Universal Product Parsing**: Python scraper extracts metadata from pasted retailer URLs to generate wishlist cards.

### Phase 3: Content & Monetization

- **Tiered Subscriptions**: Gated access enforced at both frontend routing and backend API level.
- **Pay-Per-View & Tipping**: Unlock individual posts, vault videos, or send tips in DMs.
- **Media Watermarking**: Automatic watermarking on upload, download prevention measures.

### Phase 4: Infrastructure & Performance

- **Media Delivery**: Oracle Object Storage with backend media proxy for access-controlled delivery.
- **Auto-Scaling**: Architecture designed to handle traffic spikes using OCI Flex shapes.

---

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your keys and Oracle DB details
```

### Frontend

```bash
cd frontend
npm install

cp .env.example .env
# Edit .env with your API URL and Stripe public key

npm run dev
```

---

## Environment Variables

### Backend (`backend/.env`)

```env
SECRET_KEY=your-jwt-secret
DATABASE_URL=oracle+oracledb://admin:password@brooksdb_low?wallet_location=/path/to/wallet
TNS_ADMIN=/path/to/wallet
FRONTEND_URL=http://localhost:5173

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PRICE_ID=price_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Oracle Object Storage
OCI_NAMESPACE=axawuszdq405
OCI_BUCKET=bucket-20260313-1340
OCI_REGION=us-sanjose-1
```

---

## Deployment

### Oracle Cloud Provisioning

We use automated scripts in the `grabOracle/` directory to provision OCI resources.

```bash
# Start the capacity retry loop for A1 ARM instances
bash grabOracle/oci_free_tier_provision.sh
```

### Docker (Local Production)

```bash
docker compose up --build
# App: http://localhost (Nginx on port 80)
# Health: curl http://localhost/api/health
```

---

## Next Steps

1. **Secure ARM Instance**: Wait for the `oci_free_tier_provision.sh` loop to secure capacity.
2. **Configure OCI Networking**: Ensure Security Lists allow ports 80, 443, and 8000.
3. **Initialize Database**: Run `backend/init_oracle_db.py` once compute is ready.
4. **Deploy Connect**: Set up the Stripe Connect dashboard and generate API keys.

---

## Testing

```bash
cd backend
source venv/bin/activate
pip install pytest pytest-asyncio httpx
python -m pytest tests/ -v
```

Tests use an in-memory SQLite database and mock all Stripe API calls. Coverage includes:

- **Checkout flow** — session creation, plan selection, auth gating
- **Subscription status** — active, expired (auto-marked), admin bypass
- **Customer portal** — URL generation, missing customer error
- **Webhooks** — `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, signature verification
- **End-to-end** — full lifecycle from checkout through cancellation

---

## Project Structure

```
frontend/src/
  api.js              Axios instance with JWT interceptor + 401 redirect
  router.js           Vue Router (all routes public, access enforced per-view)
  stores/auth.js      Pinia store: user, token, subscription state
  views/              Page components

backend/app/
  main.py             FastAPI app, CORS, router registration, lifespan init
  database.py         Async SQLAlchemy engine, get_db() dependency
  models.py           User, Subscription, Photo SQLAlchemy models
  auth.py             JWT creation/verification, get_current_user() dependency
  routers/            auth.py, photos.py, subscription.py, admin.py
  utils/
    s3_client.py      Storage client (OCI / S3 / local), media proxy support
    stripe_client.py  Stripe checkout, portal, webhook helpers

backend/tests/
  conftest.py         Fixtures: test DB, client, users, subscriptions
  test_payment_flow.py  Payment/subscription flow tests (25 tests)
```

Default admin credentials: `admin@rhj.com` / `admin1234`
