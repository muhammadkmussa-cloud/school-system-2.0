# School Management System — Production Deployment Guide

## Architecture Overview

```
                        ┌──────────────┐
                        │   Cloudflare │  (DNS + CDN + DDoS protection)
                        └──────┬───────┘
                               │
                    ┌──────────┴──────────┐
                    │     NGINX Reverse   │
                    │     Proxy (TLS)     │
                    └────┬──────────┬─────┘
                         │          │
              ┌──────────┴──┐  ┌───┴──────────┐
              │  FastAPI ×4 │  │  React SPA   │
              │  (Uvicorn)  │  │  (Static)    │
              └──────┬──────┘  └──────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
    ┌────┴────┐ ┌───┴────┐ ┌───┴────────┐
    │PostgreSQL│ │ Redis  │ │ S3 (Files) │
    │   16     │ │   7    │ │  R2/S3     │
    └─────────┘ └────────┘ └────────────┘
         │           │
    ┌────┴────┐ ┌───┴────────┐
    │  Daily   │ │  Celery    │
    │  Backup  │ │  Worker    │
    └─────────┘ └────────────┘
```

## Prerequisites

- Ubuntu 22.04+ server (4 GB RAM, 2 vCPU minimum)
- Domain names: `api.example.com`, `app.example.com`
- PostgreSQL 16, Redis 7, Python 3.12, Node.js 20

## Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.12 python3.12-venv python3.12-dev \
    postgresql-16 redis-server nginx certbot python3-certbot-nginx \
    build-essential libpq-dev curl git

# Start services
sudo systemctl enable --now postgresql redis-server
```

## Step 2: Database

```bash
sudo -u postgres psql <<SQL
CREATE USER school_system WITH PASSWORD 'strong-password-here';
CREATE DATABASE school_system OWNER school_system;
GRANT ALL PRIVILEGES ON DATABASE school_system TO school_system;
\c school_system
GRANT ALL ON SCHEMA public TO school_system;
SQL
```

## Step 3: Application Deployment

```bash
# Create application user
sudo useradd -m -s /bin/bash school_system
sudo mkdir -p /opt/school_system
sudo chown school_system:school_system /opt/school_system

# Clone repository
sudo -u school_system git clone https://github.com/your-org/school-system.git /opt/school_system

# Setup backend
cd /opt/school_system/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Copy and configure environment
cp /opt/school_system/deploy/.env.production /opt/school_system/.env
# EDIT /opt/school_system/.env with real values!
nano /opt/school_system/.env
```

## Step 4: Database Migrations

```bash
cd /opt/school_system/backend
source .venv/bin/activate
alembic upgrade head
python -m app.seed  # Optional: seed demo data
```

## Step 5: Systemd Services

```bash
sudo cp /opt/school_system/deploy/systemd.service /etc/systemd/system/school-system-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now school-system-api

# Verify
sudo systemctl status school-system-api
curl http://127.0.0.1:8000/health
```

## Step 6: NGINX & TLS

```bash
# Copy config
sudo cp /opt/school_system/deploy/nginx.conf /etc/nginx/sites-available/school_system
sudo ln -s /etc/nginx/sites-available/school_system /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# SSL certificates
sudo certbot --nginx -d api.example.com -d app.example.com
```

## Step 7: Frontend Build

```bash
cd /opt/school_system/frontend
npm ci
npm run build
sudo mkdir -p /var/www/school-system-frontend
sudo cp -r dist/* /var/www/school-system-frontend/
sudo chown -R www-data:www-data /var/www/school-system-frontend
```

## Step 8: Celery (Background Jobs)

```bash
# Uncomment the celery services in deploy/systemd.service
sudo cp /opt/school_system/deploy/systemd.service /etc/systemd/system/school-system-celery.service
# Edit to uncomment the [Service] sections

sudo systemctl daemon-reload
sudo systemctl enable --now school-system-celery school-system-celery-beat
```

## Step 9: Database Backups

```bash
# Add to crontab (daily at 2 AM)
sudo -u postgres crontab -e

# Add:
0 2 * * * pg_dump school_system | gzip > /var/backups/school_system/school_system_$(date +\%Y\%m\%d).sql.gz
0 3 * * * find /var/backups/school_system -name "*.gz" -mtime +30 -delete
```

## Step 10: Monitoring

```bash
# Install Prometheus node exporter
sudo apt install -y prometheus-node-exporter

# Add Sentry for error tracking (in .env)
# SENTRY_DSN=https://xxx@sentry.io/xxx
```

## Verification Checklist

- [ ] `curl https://api.example.com/health` returns `{"status": "healthy"}`
- [ ] Login endpoint works: `POST /api/v1/auth/login`
- [ ] HTTPS enforced (HTTP redirects to HTTPS)
- [ ] Rate limiting active (rapid requests get 429)
- [ ] API docs accessible: `https://api.example.com/docs`
- [ ] Frontend loads: `https://app.example.com`
- [ ] Database backups running

## Scaling

| Load | Configuration |
|------|--------------|
| < 5 schools | Single server, 2 workers |
| 5–20 schools | 4 workers, 2 vCPU, 4 GB RAM |
| 20–100 schools | 8 workers, load balancer, read replica |
| 100+ schools | Kubernetes, sharded by school_id |

## Multi-Region

For schools across Africa, deploy API servers in:
- **Nairobi** (AWS/GCP/Azure region) — East Africa
- **Lagos** — West Africa
- **Cape Town** — Southern Africa

Use Cloudflare or AWS Global Accelerator for latency-based routing.

## Curriculum Flexibility

The platform supports configurable curricula — the same codebase serves:
- 🇰🇪 CBC Kenya
- 🇰🇪 8-4-4 (KCSE)
- 🌍 Cambridge IGCSE
- 🌍 IB Diploma
- 🇳🇬 Nigeria BEC (WAEC)
- 🇿🇦 South Africa CAPS

New curricula are added as data (not code) through the curriculum service.
Each school selects its curriculum at setup; grading, levels, and
promotion paths adapt automatically.
