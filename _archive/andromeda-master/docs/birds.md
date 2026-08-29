# birds

`@refrens/birds` — a shared library used by **both backend and frontend** repos. The backend
services consume its Feathers.js hooks and service abstractions; the frontend apps import its
framework-agnostic helper utilities. Centralises cross-cutting logic so repos don't duplicate it.

**Tech:** TypeScript, Feathers v4, Mongoose
**Tags:** packages, backend-core, backend-ai, full-stack

## What it contains

- `src/hooks/` — Feathers before/after/error hooks (fast-populate, mongo-search, rate-limit,
  auth strategy, vault-secret, Sentry/xray) — consumed by the backend services.
- `src/services/` — shared Feathers/Mongoose service abstractions (`FlexStore`, `MongooseService`,
  `MongooseEmbedded`).
- `src/helpers/` — framework-agnostic utilities used by the **frontend** apps (image/srcset
  optimisation, date/time formatting, unit & price conversion, record normalisation, CSV
  validators, state utils) as well as the backend.
- `src/constants/`, `src/lib/` (e.g. `SecretVault`), and shared `src/types`.

## Consumed by

- **Backend:** `serana`, `astrid`, `courier` (Feathers hooks + services).
- **Frontend:** `lydia`, `elisif`, `phobos`, `jupiter` (mostly the `helpers/` utilities).

## When to reach for it

- Adding/changing a Feathers hook or service abstraction reused across backend services.
- Adding/changing a shared helper utility imported by the frontend apps (image/srcset, date,
  unit/price conversion, normalisation, CSV validation).
- Updating shared constants or type definitions used across repos.
