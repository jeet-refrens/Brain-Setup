# seeds

Node.js (`.mjs`) utilities for Refrens data tooling (also known as Sandesh). Two major functions: Elastic ↔ Mongo synchronization, and data seeding / migration / sitemap generation.

**Tech:** Node.js (.mjs scripts), Elasticsearch, MongoDB / Mongoose, Commander (CLI), CSV
**Tags:** tools

## What it contains

- Elastic ↔ Mongo sync (esSync): `essync.mjs`, `esTransformConfig.mjs`, and `indexmonitor.mjs` — syncing MongoDB data into Elasticsearch and monitoring the indexes.
- Seed scripts for major MongoDB collections.
- CSV import utilities for bulk data loading.
- One-off production data migration scripts.
- Reference data population (e.g. HSN codes, state lists).
- SEO sitemap generation.

## When to reach for it

- Working on Elastic ↔ Mongo sync — the esSync scripts or index monitoring.
- Writing a one-off data migration against production MongoDB.
- Seeding dev/staging databases with test data.
- Adding a bulk CSV import or reference-data population script.
- Changing how SEO sitemaps are generated.
