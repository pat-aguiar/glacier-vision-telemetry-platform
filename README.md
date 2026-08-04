# Vision Telemetry Platform

A real-time telemetry ingestion and monitoring platform for AI-powered edge computer-vision hardware. Edge devices report classification events (label, confidence score, bounding boxes) to a FastAPI backend, which persists them to a partitioned Postgres store and streams them live to a React dashboard over WebSockets.

**Live demo:** https://23-20-203-22.sslip.io/
**Repository:** https://github.com/pat-aguiar/glacier-vision-telemetry-platform

> The live demo runs against continuously-generated synthetic telemetry (no physical hardware attached) so the dashboard always shows live activity.

---

## Features

- **Idempotent event ingestion** — edge devices with unreliable network connections can safely retry a POST; duplicate `event_id`s are detected and replayed as a 200 instead of creating a second row.
- **Live dashboard streaming** — a WebSocket pub/sub broadcaster pushes every new telemetry event to all connected dashboard clients in real time, with origin validation and token auth at the handshake.
- **Resilient frontend connection handling** — the dashboard's WebSocket client auto-reconnects on drop with exponential backoff and jitter, and visibly surfaces connection state (connected / reconnecting / disconnected) rather than failing silently.
- **Partitioned, time-series-ready schema** — `sorting_events` is a native Postgres table partitioned by `occurred_at`, with facility/device-scoped indexes so both dashboard queries and future partition pruning stay cheap as volume grows.
- **Dual authentication model** — a constant-time-compared `X-API-Key` for edge devices submitting events, and a separate `X-Dashboard-Token` (plus WebSocket query-param token) for read/dashboard clients, so ingestion and read credentials can be rotated independently.
- **Defense-in-depth request handling** — a custom ASGI middleware enforces a request body size ceiling (checked both via `Content-Length` and as bytes stream in, so chunked encoding can't bypass it), and ingestion is rate-limited per client.
- **Consistent error contract** — a single `AppError` hierarchy and global exception handlers normalize every failure (validation, not-found, conflict, rate limit) into one JSON error envelope, so API consumers never have to branch on error shape.
- **Layered backend architecture** — routes depend only on injected services, services depend only on injected repositories/collaborators, matching FastAPI's own `Depends()`-based DI pattern end-to-end rather than routes reaching into the database or singletons directly.
- **Mock vision provider** — deterministic, seeded bounding-box/label generation stands in for a real inference pipeline, so the full ingestion → storage → dashboard path is demonstrable without physical edge hardware.

## Architecture

```
Edge device ─POST /api/v1/telemetry/events──▶ FastAPI ──▶ Repository ──▶ Postgres (partitioned)
                                                 │
                                                 ▼
                                           Broadcaster (pub/sub)
                                                 │
Dashboard  ◀──WSS /api/v1/telemetry/stream────── nginx (TLS termination, same-origin proxy)
```

- **`app/api`** — thin controllers (HTTP + WebSocket routes), auth dependencies.
- **`app/services`** — business logic (e.g. `TelemetryService`: device lookup, idempotent insert, conditional broadcast).
- **`app/repositories`** — persistence, isolated behind a small interface per aggregate (`SortingEventRepository`, `DeviceRepository`).
- **`app/streaming`** — the in-process WebSocket broadcaster singleton.
- **`app/mock_vision`** — synthetic bounding-box generation standing in for a real CV inference service.

In production, nginx terminates TLS and reverse-proxies `/api/` and `/static/` to the backend on the same origin the page is served from — the frontend never needs to know its own deployed hostname at build time.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic |
| Database | PostgreSQL 16 (native range partitioning), asyncpg |
| Real-time | WebSockets, custom pub/sub broadcaster |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Chart.js |
| Testing | pytest, pytest-asyncio, httpx / httpx-ws (backend); Vitest, Testing Library (frontend) |
| Infrastructure | Docker, Docker Compose, nginx, AWS EC2, Let's Encrypt (Certbot) |

## Getting Started

### Prerequisites
- Docker and Docker Compose

### Local setup

```bash
git clone https://github.com/pat-aguiar/glacier-vision-telemetry-platform.git
cd glacier-vision-telemetry-platform
cp .env.example .env   # fill in generated secrets, see below
docker compose up -d --build
```

The dashboard is served at `http://localhost:3000`, the API at `http://localhost:3000/api/v1`, and interactive API docs (Swagger UI) at the backend's `/docs`.

To see live data without physical hardware, run the synthetic event generator against the running stack:

```bash
python scripts/mock_event_generator.py --devices 3 --rate 2 --count 0
```

### Environment variables

See `.env.example` for the full list. The required ones:

| Variable | Purpose |
|---|---|
| `POSTGRES_PASSWORD` | Database password; also used to construct `DATABASE_URL` |
| `EDGE_API_KEY` | Shared secret edge devices send via `X-API-Key` to ingest events |
| `DASHBOARD_ACCESS_TOKEN` | Token dashboard clients use to read data (HTTP header + WebSocket query param) |

Generate secrets with `openssl rand -base64 32`.

## Running Tests

```bash
# Backend (requires the dockerized Postgres to be running)
pip install -e ".[dev]"
pytest

# Frontend
cd frontend
npm install
npm run test
```

## API Overview

Full interactive documentation is available at `/docs` (Swagger) once the backend is running. Key endpoints:

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/telemetry/events` | `X-API-Key` | Ingest a telemetry event (idempotent on `event_id`) |
| `GET` | `/api/v1/telemetry/events/{id}/image` | `X-Dashboard-Token` | Fetch the captured frame + bounding boxes for an event |
| `WS` | `/api/v1/telemetry/stream?token=...` | Dashboard token (query param) | Live feed of newly ingested events |

## Deployment

The live demo runs on a single AWS EC2 instance via Docker Compose: Postgres, the FastAPI backend, the React frontend behind nginx, and a background service that continuously generates synthetic telemetry so the dashboard always shows activity. nginx terminates HTTPS with a free Let's Encrypt certificate (auto-renewing) and redirects all HTTP traffic to HTTPS.
