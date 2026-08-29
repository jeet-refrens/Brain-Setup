# Shopify Integration Revamp — Summary

## State of the world

The current `shopifyApp` does exactly one thing: Shopify order → Refrens invoice (+ payment + email + refund/cancel handling) via five webhooks processed inline on the request thread. Products and inventory are completely absent. Mandatory GDPR webhooks are stubbed (`server/controllers/gdpr.js:16,53`). Merchants paste `refrensApiKey`/`refrensSecretKey` into the embedded admin and these are stored **in plaintext** (`prisma/schema.prisma:19-20`). Webhook handlers have no event-id dedup, no retry/DLQ, no replay; idempotency is hacked through one boolean (`createdOnRef`) and one JSON blob (`refundedItems`). On the Serana side, all invoice/creditnote/payment endpoints the bridge needs exist and work, but there is **no outbound event mechanism** — nothing to subscribe to for "invoice paid in Refrens" or "stock changed in Refrens", which blocks any Refrens→Shopify direction.

## Top 3 problems

1. **No product/inventory bridge.** Refrens has a deep stock engine (UPDATE/BLOCK/IGNORE/BLOCK_IGNORE modes, batch + serial + package tracking, per-warehouse, concurrency-controlled retry up to 20×) that Shopify never touches.
2. **Webhook reliability is a single thread.** `server/index.js:77-94` processes everything inline; no `X-Shopify-Event-Id` dedup; Shopify's current retry policy is **8 attempts over 4 hours** with auto-unsubscribe on consecutive failures — the current code is one slow Refrens day away from being kicked off webhook delivery.
3. **REST legacy + security wart.** REST has been legacy since 2024-10-01; new public apps must be GraphQL since 2025-04-01. Plus `app_uninstalled.js:19-29` hard-deletes the Store row (drops `refrensToken`/keys/billing history); `GlobalRoutes.jsx:31` references an unimported `Setup` component (runtime error); `app_proxy/onboarding.js:9` and `billing.js:56-79` write to models/fields not declared in `schema.prisma`.

## Top 3 recommendations

1. **Make shopifyApp a thin, reliable bridge.** Persist every webhook in a `WebhookEvent` table keyed on `X-Shopify-Event-Id`, ACK in <200ms, do all Refrens calls in a BullMQ worker with retries + DLQ + replay.
2. **Build a Refrens-owned bridge surface in Serana.** Idempotent "set absolute stock for SKU at warehouse" endpoint, outbound events for "invoice paid"/"stock changed" (none today), and an OAuth-style authorize page to replace the API-key paste UX.
3. **GraphQL for new code, REST stays for now** behind a thin facade; webhook subscriptions via `shopify.app.toml` (including `compliance_topics`, api_version 2026-01).

## Smallest demo prototype

Rebuild only `orders/create → Refrens invoice` on the new architecture: persisted event log, BullMQ worker, idempotency-keyed Refrens POST, plus a Polaris "Sync Status" page showing the last 50 events. Force a duplicate delivery (Shopify CLI `webhook trigger`) — prove no duplicate invoice. Force a Serana 500 — prove retry then DLQ then Sentry alert. **One engineer, one week.** No new Serana endpoints needed.

## Ask Serana team (priority order)

1. OAuth-style authorize endpoint for app installs (kill the API-key paste).
2. Honor `Idempotency-Key` on POST `/invoices`, `/payments`, `/creditnotes`.
3. New idempotent single-SKU stock-set endpoint: `POST /businesses/:business/inventory-adjustments` with `(sku, warehouse, finalStock, externalEventId)`.
4. Outbound webhook mechanism — biggest Serana-side gap; blocks two-way sync.
5. Anonymize-contact-by-email op for `customers/redact`.
6. Where to store the variant↔inventory mapping (local Postgres vs `externalRefs[]` on Talos schema).
7. Per-business rate-limit docs.
8. Make `shopifyOrderNumber` queryable on invoices for reconciliation.

## P0 changes for shopifyApp

1. `WebhookEvent` table + dedup by `X-Shopify-Event-Id` (~1d).
2. BullMQ + Redis; all current handlers become jobs (~3d).
3. Encrypt `refrensApiKey`/`refrensSecretKey` at rest using existing Cryptr (<½d + migration).
4. Fix `app_uninstalled.js` to set `isActive=false` only — keep all other fields (<½d).
5. Register mandatory compliance webhooks via `shopify.app.toml compliance_topics` + actually implement `customers/data_request`, `customers/redact` (~1d).
6. Fix the three latent broken references above (~½d).

Full report (gap tables per resource, target architecture diagram, four data-flow walkthroughs, full P0/P1/P2/P3 changelist, assumptions, open questions): `blueprint.md`.
