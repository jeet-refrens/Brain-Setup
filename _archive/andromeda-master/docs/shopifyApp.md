# shopifyApp

A Shopify integration that lets merchants use Refrens for invoicing and accounting. Combines a React embedded app (rendered inside Shopify Admin) with an Express backend that handles Shopify OAuth, webhooks, and order synchronization.

**Tech:** Express, React (Vite), PostgreSQL (Prisma), Shopify GraphQL Admin API, Shopify Polaris, JavaScript
**Tags:** backend

## What it contains

- Shopify OAuth and session management in `server/shopify.js` (App Bridge token exchange).
- Webhook handlers in `server/webhooks/` for Shopify events such as `orders/create`.
- Sync logic in `server/controllers/sync.controller.js` that turns Shopify orders into Refrens invoices.
- A React (Vite) embedded UI in `src/` built with Shopify Polaris components — Settings and Dashboard pages under `src/pages/`.
- Prisma schema/client persisting Shopify store sessions and app configuration in PostgreSQL.

## When to reach for it

- Changing the Shopify OAuth/install flow or session handling.
- Working on order sync from Shopify into Refrens invoices, or adding new webhook handlers.
- Editing the embedded merchant UI (Polaris pages/components in the Shopify Admin).
- Updating the Prisma schema for Shopify session/configuration storage.
