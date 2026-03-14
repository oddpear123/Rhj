# =============================================================================
# Multi-stage Dockerfile for Cloud deployment (OCI/Generic)
# Combines Vue frontend (Nginx) + FastAPI backend (Gunicorn) + supervisord
# =============================================================================

# --- Stage 1: Build the Vue frontend ---
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .

# Vite bakes VITE_* env vars at build time
ENV VITE_API_URL=/api
ARG VITE_STRIPE_PUBLIC_KEY=""
ENV VITE_STRIPE_PUBLIC_KEY=$VITE_STRIPE_PUBLIC_KEY

RUN npm run build

# --- Stage 2: Final image ---
FROM python:3.12-slim

# Install nginx and supervisor
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx supervisor && \
    rm -rf /var/lib/apt/lists/*

# --- Backend setup ---
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Create uploads directory for local storage fallback
RUN mkdir -p /app/uploads/photos /app/uploads/previews

# --- Frontend setup ---
# Copy built frontend assets to Nginx html root
COPY --from=frontend-builder /frontend/dist /usr/share/nginx/html

# --- Nginx config ---
COPY nginx.conf /etc/nginx/sites-available/default
# Remove the default nginx config that conflicts
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# --- Supervisord config ---
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Standard web port
EXPOSE 80

# Run supervisord to manage both nginx and gunicorn
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
