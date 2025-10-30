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

### Gamification service

The `backend.services.gamification` module implements score tracking, leaderboard updates, and achievement unlocking backed by Redis. Instantiate the service with a Redis client—either via `get_gamification_service()` or by passing an existing client to `GamificationService`. Helper methods are available for the key application events:

- `record_vote` adjusts the `leaderboard:score` sorted set and unlocks the **Meme Lord** achievement once a user accrues 100 or more upvotes.
- `record_upload` tracks per-user upload counts, awarding **First Upload** the first time a creator submits content.
- `record_daily_visit` records unique daily visitors in Redis sets keyed by date and unlocks **Daily Visitor** on the first unique visit.
- `record_timer_submission` updates the timer leaderboard, using an optimistic transaction to determine whether a participant has entered the top ten and unlocking the **Top Timer** achievement accordingly.

Each helper returns a `GamificationEventResult` detailing newly unlocked achievements alongside contextual data (for example, updated scores or leaderboard ranks). Achievements are persisted in Redis sets so repeated triggers remain idempotent.

## Infrastructure & Operations

Infrastructure-as-code definitions, deployment configurations, and CI/CD orchestration artifacts will live under `infra/`. Docker Compose and other orchestration files will be added as part of future tickets.

## Local Development

A unified developer experience—including Docker Compose workflows for spinning up the full stack—is planned but not yet implemented. Placeholder configuration files will be introduced in forthcoming tasks as the application components take shape.

## Legacy Landing Page

The original static landing page that previously lived at the repository root has been preserved under `archive/` for reference. The assets remain unchanged and can be reused or migrated as needed.
