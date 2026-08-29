# sithis

Refrens' internal **admin panel** — a Next.js / React frontend (Ant Design) for the operations
team. It renders admin screens (dashboard, resource views) and talks to the backend APIs as a
client (Feathers `rest-client` + axios); it serves no API of its own. The admin **API** is
[astrid](astrid.md) — sithis is the panel in front of it.

**Tech:** Next.js 13, React 18, Ant Design, Feathers rest-client (runs on port 7700)
**Tags:** frontend

## What it contains

- `src/pages/` — admin UI pages (`dashboard/`, `resources/`) on the Next.js Pages Router.
- `src/components/`, `src/styles/` — Ant Design–based admin UI.
- `src/feathers.js` — Feathers REST client config pointing at the backend APIs.
- `src/hooks/`, `src/helpers/`, `src/lib/`, `src/utils/` — client-side logic.

## When to reach for it

- Adding or changing admin/back-office screens for the operations team.
- Wiring admin views to backend APIs (via the Feathers rest-client).
- Working on the Ant Design admin UI.
