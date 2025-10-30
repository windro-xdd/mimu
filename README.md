# Project Monorepo Scaffold

## Overview

This repository is transitioning into a full-stack monorepo that will eventually host coordinated frontend, backend, infrastructure, and data workloads. The current layout provides placeholders for the major components while subsequent tickets will populate each area with application code, shared tooling, and automation scripts.

## Project Structure

```
/
├─ frontend/           # Client-facing application (TBD)
├─ backend/            # Server services, APIs, background workers
│  ├─ services/        # Individual backend service entry points
│  └─ uploads/         # Local development storage (ignored in git)
├─ migrations/         # Database and data pipeline migrations
├─ infra/              # Infrastructure as code & deployment tooling
└─ archive/            # Preserved legacy static assets
```

## Frontend (placeholder)

Upcoming work will introduce a modern frontend stack and associated build tooling under `frontend/`.

## Backend (placeholder)

Backend services, APIs, and shared libraries will land under `backend/` with individual services organized inside the `services/` directory. The `backend/uploads/` directory is reserved for development-only storage and is ignored by version control except for the placeholder file that keeps the folder present.

## Infrastructure & Operations

Infrastructure-as-code definitions, deployment configurations, and CI/CD orchestration artifacts will live under `infra/`. Docker Compose and other orchestration files will be added as part of future tickets.

## Local Development

A unified developer experience—including Docker Compose workflows for spinning up the full stack—is planned but not yet implemented. Placeholder configuration files will be introduced in forthcoming tasks as the application components take shape.

## Legacy Landing Page

The original static landing page that previously lived at the repository root has been preserved under `archive/` for reference. The assets remain unchanged and can be reused or migrated as needed.
