# Project Monorepo Scaffold

## Overview

This repository is gradually evolving into a full-stack monorepo that will host coordinated frontend, backend, infrastructure, and data workloads. The current layout now includes a developer-focused Docker Compose workflow so the whole stack can be booted locally with a single command while the real application code is being implemented in follow-on tickets.

## Project Structure

```
/
├─ frontend/           # Client-facing application scaffold
│  ├─ Dockerfile       # Placeholder Node.js development server image
│  ├─ package.json     # Node manifest with a simple start script
│  └─ server.js        # Lightweight HTTP server + health check endpoint
├─ backend/            # Server services, APIs, background workers
│  ├─ app.py           # Minimal HTTP server used for local orchestration
│  ├─ Dockerfile       # Python image with boto3 installed for S3 support
│  ├─ requirements.txt # Backend Python dependencies (currently boto3)
│  ├─ services/        # Backend service entry points
│  ├─ tests/           # Backend unit tests
│  └─ uploads/         # Local development storage (ignored in git)
├─ migrations/         # Database and data pipeline migrations
├─ infra/              # Infrastructure as code & deployment tooling
│  └─ docker-compose.yml
├─ archive/            # Preserved legacy static assets
├─ .env.example        # Template of environment variables required by the stack
└─ README.md
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose v2 (ships with modern Docker Desktop and Docker Engine installations)
- Optional: access to the MinIO/S3 profile if you want to exercise the object-storage integration

## Quick start (Docker Compose)

1. **Configure environment variables**

   Copy the example file and adjust any secrets or ports to match your local setup:

   ```bash
   cp .env.example .env
   ```

   The `.env` file is consumed by `infra/docker-compose.yml` and should never be committed to version control.

2. **Start the stack**

   ```bash
   docker compose -f infra/docker-compose.yml up --build
   ```

   > ℹ️  If you use the standalone `docker-compose` binary, substitute `docker compose` with `docker-compose` in the commands above.

   This command builds the backend and frontend images, provisions PostgreSQL and Redis, and then launches the placeholder application services. Logs for every container stream to your terminal.

   - Visit the frontend placeholder at <http://localhost:3000>
   - Backend health endpoint: <http://localhost:8000/healthz>
   - PostgreSQL is exposed on port `5432`, Redis on `6379`

3. **(Optional) Enable the S3-compatible object storage profile**

   A MinIO server plus an initialization job can be started by enabling the `object-storage` profile. This is useful for exercising the storage abstraction layer against an S3 API.

   ```bash
   COMPOSE_PROFILES=object-storage docker compose -f infra/docker-compose.yml up --build
   ```

   MinIO API: <http://localhost:9000> (default credentials `minioadmin:minioadmin`)

4. **Stop the stack**

   Press `Ctrl+C`, then optionally remove containers and volumes:

   ```bash
   docker compose -f infra/docker-compose.yml down
   docker compose -f infra/docker-compose.yml down -v  # also removes persistent data
   ```

## Running services

| Service   | Purpose                                           | Default URL / Port             | Health check                     |
|-----------|---------------------------------------------------|--------------------------------|----------------------------------|
| frontend  | Placeholder Node.js server w/ health endpoint     | <http://localhost:3000>        | `GET /healthz`                   |
| backend   | Minimal Python HTTP server + storage stub         | <http://localhost:8000>        | `GET /healthz`                   |
| postgres  | PostgreSQL 15 database                            | `localhost:5432`               | `pg_isready`                     |
| redis     | Redis 7 cache / queue                             | `localhost:6379`               | `redis-cli ping`                 |
| minio*    | S3-compatible object storage emulator (optional)  | API `localhost:9000`, Console `localhost:9001` | `mc ls` readiness (in init job) |

\* MinIO only runs when the `object-storage` profile is enabled.

### Storage configuration

- Local uploads are persisted inside the `backend_uploads` Docker volume and mapped to `backend/uploads/` for parity with the filesystem storage backend.
- Switching to S3/MinIO is as simple as updating the variables in `.env` (set `STORAGE_BACKEND=s3` and ensure the MinIO profile is enabled). The `minio-init` service will automatically create the bucket defined by `STORAGE_S3_BUCKET` and allow anonymous download access for convenience.

### Development tips

- Environment variables documented in `.env.example` cover database URLs, Redis configuration, JWT secrets, CORS rules, cookie settings, and storage backends.
- The backend and frontend containers mount the local source directories so code changes are immediately reflected while the containers are running. Restart the affected service (`docker compose ... up backend`) if you modify dependencies.
- Use `docker compose -f infra/docker-compose.yml logs -f <service>` to tail logs for a specific container.

## Legacy landing page

The original static landing page that previously lived at the repository root is preserved under `archive/` for reference. The assets remain unchanged and can be reused or migrated as needed.
