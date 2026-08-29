# marika

A multi-tenant, customer-facing subscription-commerce product — the app Refrens' customers use to sell and manage subscriptions to *their own* end-customers (not Refrens' internal billing). Covers the full subscription commerce lifecycle on PostgreSQL.

**Tech:** Feathers v5 (Koa), TypeScript, PostgreSQL (Knex), Redis + BullMQ, TypeBox, Vitest
**Tags:** backend

## What it contains

- Offerings and `price-plans` services — products, plans, pricing, levels, and recurrence periods.
- Entitlements / `features` — gating access based on the active plan and version.
- Checkouts / carts, coupons.
- `payments` service with webhooks and payment-gateway integrations.
- `bull-queue` workers for dunning, renewals, and fulfillment.
- Cron commands and incoming webhook handlers under `src/commands/cron/` and `src/services/webhooks/`.

## When to reach for it

- Defining or editing offerings, price plans, pricing tiers, or recurrence periods.
- Working on entitlement/feature gating.
- Building checkout/cart, coupon, or payment/webhook flows.
- Adding background jobs for renewals, dunning, or fulfillment via BullMQ.
