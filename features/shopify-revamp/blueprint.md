# Shopify ↔ Refrens Integration — Revamp Blueprint

Research date: 2026-05-12
Author: Claude (research session)
Scope: Refrens' existing Shopify app (`shopifyApp` repo), Refrens' backend (`serana`), and the Shopify REST Admin Orders / Products / Inventory / Webhooks surface. Out of scope: Checkout Extensions, Fulfillment Service apps, B2B, Hydrogen, Storefront API, Functions.

---

## 1. Executive summary

**Current shape (one paragraph).** Refrens already ships a working, in-production Shopify public app that does exactly one job: when a Shopify order is created, it posts an invoice to the merchant's Refrens business; when the order is paid it logs a payment; when refunded it issues a credit note; when fully refunded it cancels the invoice. Everything else — products, inventory, multi-location stock, GDPR redaction, webhook idempotency, retries, observability — is either stubbed, half-built, or missing. Auth between shopifyApp ↔ Serana is bolted on as an "app-secret → app-token" exchange using a per-merchant API key pasted by the user into the embedded admin UI; there is no OAuth-style trust between the two systems. The codebase is on `@shopify/shopify-api@11.x` and pinned to a REST-resource bundle (`shopify.js:5`) — and Shopify has declared REST legacy as of 2024-10-01.

**Top 3 problems.**

1. **No product / inventory bridge at all.** The app currently treats Shopify as an order source and Refrens as an invoice sink. Inventory in Refrens has a deep stock engine (`UPDATE`/`BLOCK`/`IGNORE`/`BLOCK_IGNORE`, batch + serial + package, per-warehouse, concurrency-controlled — see `serana/docs/inventory.md`) but Shopify never touches it. Merchants who use Refrens stock tracking and sell on Shopify see Refrens stock go stale the moment a Shopify order ships.
2. **Reliability gaps in webhook handling.** `server/index.js:77-94` accepts every webhook, hands it to `shopify.webhooks.process`, and `console.log`s the result. There is no idempotency key store (no `X-Shopify-Event-Id` dedup), no retry/DLQ, no replay capability, no separation of fast-ack from slow-process. The `orders_updated` handler (`server/webhooks/orders_updated.js`) runs every external API call inline in the request thread — meaning Shopify will retry on any timeout and re-create credit notes. The current `Order` row only protects the *invoice create* path (via `createdOnRef`); refunds and payments are not similarly guarded.
3. **REST migration debt + non-prod hygiene.** REST is legacy. The whole app uses REST resources (`shopify.js:5`, plus the REST `shopify.rest.Shop.all` call in `server/middleware/auth.js:243`) and one-off GraphQL calls for billing. New public apps as of 2025-04-01 must be GraphQL-only; existing apps will follow. Also: the app stores `refrensApiKey` / `refrensSecretKey` *unencrypted* in Postgres (`prisma/schema.prisma:19-22`), while it bothers to encrypt the much-less-sensitive Shopify session blob (`utils/sessionStorage.js:33`). The current handler in `app_uninstalled.js:19-29` does a hard delete-and-recreate of `Store` which races with concurrent webhooks and discards billing history.

**Top 3 recommendations.**

1. **Treat shopifyApp as a thin, reliable bridge.** Move ALL business logic (mapping, idempotency, retry, reconciliation) to a job queue with a durable record of every Shopify event received, every Refrens call attempted, and the result. Webhook HTTP handler returns 200 in <200ms after persisting the event; a worker drains the queue.
2. **Add a Refrens-owned "shopify-bridge" surface in Serana (or as a sidecar).** shopifyApp becomes a translator only. The bridge holds the merchant↔business mapping, exposes idempotent endpoints that shopifyApp can hit with a per-shop bearer token (replace the user-pasted API key with a one-time OAuth-during-install handshake), and emits outbound events Serana cares about. This is also where the inventory two-way sync lives.
3. **Plan for GraphQL from day one.** Build the new bridge with `@shopify/shopify-api` GraphQL clients and the new GraphQL `webhookSubscriptionCreate`. Keep REST only where the GraphQL equivalent doesn't yet exist (and tag every such use). Subscribe to webhooks via `shopify.app.toml`, not at runtime registration in `auth/tokens` (which silently fails for compliance topics today — see `server/middleware/auth.js:172-181`).

The rest of this document spells out the current state, the gap, the target architecture, the prioritized change list, and the smallest prototype that proves the bridge works.

---

## 2. Current state — shopifyApp

### 2.1 Top-level map

| Concern | File | Notes |
|---|---|---|
| Express boot, webhook dispatch | `server/index.js` | Single `/webhooks/:topic` route, all topics share one Express handler |
| Shopify client config | `server/shopify.js` | REST resources pinned per `SHOPIFY_API_VERSION` env (`shopify.js:5`) |
| OAuth + onboarding | `server/middleware/auth.js` | `/auth`, `/auth/tokens`, `/auth/callback`; also creates lead + Slack ping on first install |
| Session HMAC verify | `server/middleware/verifyRequest.js` | Uses App Bridge bearer; redirects on 401 |
| Generic HMAC | `server/middleware/verifyHmac.js` | Used only for GDPR routes (not for the main `/webhooks/:topic` — that path relies on `shopify.webhooks.process`) |
| Proxy signature | `server/middleware/proxyVerification.js` | Verifies app-proxy storefront requests |
| Active-shop guard | `server/middleware/isActiveShop.js` | Redirects un-installed shops back through `/auth` |
| Error handling | `server/middleware/errorHandler.js` | Sends to Sentry if `REFRENS_ENV in {production, staging}` |
| CSP | `server/middleware/csp.js` | Sets frame-ancestors for embedded admin |
| Webhook: APP_UNINSTALLED | `server/webhooks/app_uninstalled.js` | Hard-deletes and recreates `Store`; mis-uses Prisma model singletons (line 7) |
| Webhook: ORDERS_CREATE | `server/webhooks/orders_created.js` | The main path: order → invoice POST → optional payment POST → optional email POST |
| Webhook: ORDERS_PAID | `server/webhooks/orders_paid.js` | Posts a `payments` record on an already-created invoice |
| Webhook: ORDERS_UPDATED | `server/webhooks/orders_updated.js` | Refund handling: full refund → invoice `status=CANCELED`; partial → credit note |
| Webhook: ORDERS_CANCELLED | `server/webhooks/orders_cancelled.js` | Cancels the invoice |
| Webhook: APP_SUBSCRIPTIONS_UPDATE | `server/webhooks/app_subscriptions_update.js` | Tracks Refrens Essentials / Enterprise plan status |
| GDPR routes | `server/controllers/gdpr.js` | `customers_data_request` and `customers_redact` are no-ops; `shop_redact` deletes Store. Not registered via Shopify webhook subscriptions — the URLs are exposed and merchant must configure them in the Partner Dashboard manually (see `SETUP.md:52-55`) |
| User-facing API | `server/routes/storeSettings.js` | `/getStoreSettings`, `/updateStoreSettings` (validates Refrens API key, exchanges for token), `/updateStoreAutoSend` |
| Billing routes | `server/routes/billing.js`, `subscriptionRegular.js`, `subscriptionEnterprise.js`, `_recurringSubscriptions.js` | App-subscription create + metafield writing — uses GraphQL Admin |
| App proxy routes | `server/routes/app_proxy/*.js` | `/onboarding/1`, `/shopDetails` — the `/onboarding/1` route writes to a `onboardingFlow` table that is NOT declared in `prisma/schema.prisma` (latent bug, will throw at runtime) |
| Debug routes | `server/routes/debugRoutes.js` | `/gql` test query |
| Refrens API helper | `utils/checkRefrensToken.js` | Token refresh logic: ping `/authentication` with `strategy: 'app-token'`; if 401, exchange `appId`+`appSecret` |
| HMAC for Refrens leads | `utils/signRequest.js` | Signs lead creation with `SERANA_API_KEY` — used in `auth.js:46` for the on-install lead. This is the only place shopifyApp signs requests to Serana with the shared HMAC scheme |
| Currency helpers | `utils/utils.js` | GST state map, `getItemsPayload`, `roundToFixed`, tax-from-total math |
| Prisma session storage | `utils/sessionStorage.js` | Encrypts session JSON with `Cryptr` |
| OAuth redirect helper | `utils/authRedirect.js` | App Bridge exitframe + offline auth begin |
| Front-end shell | `src/App.jsx`, `src/GlobalRoutes.jsx` | App Bridge + Polaris + Apollo + react-query. `GlobalRoutes.jsx:31` references `<Setup />` but `Setup` is not imported → broken route at runtime |
| Front-end pages | `src/pages/Index.jsx`, `Configurations.jsx`, `Settings.jsx`, `Dashboard.jsx`, `Help.jsx` | Index = "Connect your Refrens Account"; Configurations = `autoSendInvoice` toggle |

### 2.2 Shopify entity → Refrens entity → file → status

| Shopify | Refrens | Direction | File | Status |
|---|---|---|---|---|
| `orders/create` | `POST /businesses/:business/invoices` | Shopify → Refrens | `server/webhooks/orders_created.js:108` | Working (inline, no retry) |
| `orders/paid` | `POST /businesses/:business/invoices/{id}/payments` | Shopify → Refrens | `server/webhooks/orders_paid.js:38` | Working (paymentMethod hard-coded to `CASH`) |
| `orders/updated` (partial refund) | `POST /businesses/:business/creditnotes` | Shopify → Refrens | `server/webhooks/orders_updated.js:183` | Working (idempotency via `refundedItems` JSON on Order row — fragile) |
| `orders/updated` (full refund) | `PATCH /businesses/:business/invoices/{id}` with `status:CANCELED` | Shopify → Refrens | `server/webhooks/orders_updated.js:96` | Working |
| `orders/cancelled` | `PATCH .../invoices/{id}` with `status:CANCELED` | Shopify → Refrens | `server/webhooks/orders_cancelled.js:38` | Working |
| invoice email | `POST .../invoices/{id}/email` | Shopify → Refrens | `server/webhooks/orders_created.js:160` | Working (gated by `autoSendInvoice`) |
| app/uninstalled | (none — local Store row reset) | Shopify → local | `server/webhooks/app_uninstalled.js` | Buggy: hard-deletes Store then recreates, dropping billing + tokens |
| app_subscriptions/update | local `Subscription` row | Shopify → local | `server/webhooks/app_subscriptions_update.js` | Working but only catches `Refrens *` plans (`app_subscriptions_update.js:8`) |
| products/* | — | — | — | **Not implemented** |
| inventory_levels/* | — | — | — | **Not implemented** |
| inventory_items/* | — | — | — | **Not implemented** |
| customers/data_request | (no-op) | Shopify → Refrens | `server/controllers/gdpr.js:16` | Stub — prints and returns success |
| customers/redact | (no-op) | Shopify → Refrens | `server/controllers/gdpr.js:53` | Stub |
| shop/redact | local `Store` delete | Shopify → local | `server/controllers/gdpr.js:87` | Working but doesn't touch Refrens |
| Refrens lead on install | `POST /leads` (HMAC-signed) | shopifyApp → Refrens | `server/middleware/auth.js:14-65` | Working — uses `signRequest` + `X-Refrens-App-Req: shopify` |

### 2.3 Auth & session model

There are **two distinct auth surfaces** that need to be kept straight:

- **Shopify → shopifyApp:** standard online + offline OAuth. Sessions are stored in Postgres `Session` table (`prisma/schema.prisma:46-53`), encrypted by `Cryptr` with `ENCRYPTION_STRING` (`utils/sessionStorage.js:12,33`). Webhooks are registered server-side at `auth/tokens` (`server/middleware/auth.js:169`), and the per-topic HMAC verification is delegated to `shopify.webhooks.process` (the SDK-managed path).
- **shopifyApp → Serana:** the merchant pastes a Refrens `appId` + `appSecret` (plus `urlKey`) into `Index.jsx`. Server calls `POST /authentication { strategy: 'app-secret', appId, appSecret }` (`server/routes/storeSettings.js:14`), gets back an `accessToken` + payload exp, stores them in `Store.refrensToken` / `tokenExpiresAt`. On token expiry it pings `/authentication { strategy: 'app-token' }`; on 401 it re-exchanges via `app-secret` (`utils/checkRefrensToken.js:29-86`). `refrensApiKey` and `refrensSecretKey` are stored **in plaintext** on `Store` (`schema.prisma:19-20`). This is a real footgun — a Postgres dump compromises every merchant's Refrens account.

A separate HMAC scheme exists for one specific call: lead creation on install signs with `SERANA_API_KEY` via `utils/signRequest.js` and Serana's `RefrensAppStrategy` (`serana/src/authentication/RefrensAppStrategy.js`). This is currently the only "system-to-system" trust between the two repos. We should expand it.

### 2.4 Data model

```
Store (one per shopify shop domain)
├── shop                   # @id, "{name}.myshopify.com"
├── isActive               # set false on uninstall (sort of)
├── refrensApiKey/Secret   # PLAINTEXT — fix
├── refrensUrlKey          # the slug used in /businesses/:urlKey/* routes
├── refrensToken           # the exchanged bearer
├── tokenExpiresAt
├── autoSendInvoice        # default true
└── onboardMailSent        # one-shot

Order
├── orderId                # Shopify numeric id, stringified
├── storeId                # FK Store.shop
├── invoiceId/Number       # Refrens identifiers
├── refundedItems          # Json — idempotency for partial-refund credit notes
└── createdOnRef           # idempotency for invoice create

Session  — encrypted Shopify session blob
Subscription — Shopify billing charge id + plan name
```

A few schema problems jumped out:
- `app_uninstalled.js:21-29` calls `prisma.store.delete(...).create({...})` — racy, and `refrensApiKey`, `refrensToken` etc are dropped without warning. If the same merchant reinstalls they have to re-paste API keys.
- `app_proxy/onboarding.js:9` writes to `prisma.onboardingFlow` which is not declared in `schema.prisma`. Will throw.
- `billing.js:56-79` writes to `store.appInstallationId` which is also not declared in `schema.prisma`. Will throw.
- `Order.refundedItems` is a free-form Json blob used as a partial-refund idempotency mechanism (`orders_updated.js:200-204`). It works but it's brittle: there's no per-credit-note record, and re-running the same webhook by Shopify (legitimate retry) gets prevented only because the first call sets this field.

### 2.5 Known unfinished work (from TODO + code)

- `TODO.md:3` — "Theme extension" (placeholder; `extensions/theme-extension` has a `.env.example` and a `styles.css` but no logic).
- `tmp/` is empty (just a `.gitkeep`) — no captured fixtures.
- `gdpr.js` has a `//SPECTOR:- Why is GDPR content not updated?` comment, suggesting these handlers were known to be stubs.
- `auth.js:265` has a commented-out `sendOnboardingEmails(details, store)` — onboarding email flow is dead.
- `Setup.jsx` is lorem-ipsum.
- Console.log everywhere, Sentry only fires when `REFRENS_ENV` ∈ {production, staging} — local + dev errors are lost.

---

## 3. Current state — Serana surface relevant to Shopify

Serana is a FeathersJS 4.x service-and-hook codebase on top of Mongoose, with a custom `FlexStoreFactory` wrapper (`@refrens/birds`) and shared schemas (`@refrens/talos`). Cited from `serana/CLAUDE.md`.

### 3.1 Endpoints shopifyApp uses today

All routes resolved via Feathers `app.use(...)` registrations in service factories.

| HTTP | Route | Service file | Use |
|---|---|---|---|
| POST | `/authentication` | `src/authentication/AuthFactory.js:53-56` | Token exchange: `strategy: 'app-secret' → accessToken`; `strategy: 'app-token' → 401 if expired` |
| POST | `/businesses/:business/invoices` | `src/services/business-invoices/invoices.service.js:72` | Create invoice |
| PATCH | `/businesses/:business/invoices/:id?cancelPayment=true` | same | Cancel invoice |
| POST | `/businesses/:business/invoices/:invoice/payments` | `src/services/invoice-payments/service.js:33` | Record payment |
| POST | `/businesses/:business/invoices/:invoice/email` | `src/services/invoice-share-email/invoice-share-email.service.js:25` | Email invoice PDF to client |
| POST | `/businesses/:business/creditnotes` | `src/services/business-creditnotes/creditnotes.service.js:66` | Issue credit note |
| POST | `/leads` (HMAC signed) | `src/services/leads/leads.hooks.js` (+ `src/hooks/seed-shopify-lead.js`) | On-install lead with `X-Refrens-App-Req: shopify` |

The Shopify path injects a `shopifyOrderNumber` field into the invoice payload (`orders_created.js:78`, `orders_updated.js:124`). Serana invoice schema accepts this through pass-through and it ends up indexed in Elastic — useful for reconciliation later.

### 3.2 Endpoints relevant but not currently used by shopifyApp

Discovered by grep across `src/services/`:

| Route | Service | Why interesting |
|---|---|---|
| `/businesses/:business/inventories` | `src/services/inventories/inventories.service.js:59` | The inventories CRUD — full doc in `serana/docs/inventory.md`. Supports SKU lookup via `$exists`/`$regex` whitelist. |
| `/businesses/:business/products` | `src/services/products/products.service.js:31` | Refrens' own product catalog (separate from inventories — products are catalog entries, inventories are stock units) |
| `/businesses/:business/inventory-transactions` | (internal — `disallow('external')` per `serana/docs/inventory.md` §11) | All stock writes go through this, never directly. |
| `/businesses/:business/warehouses` | `src/services/warehouses/` | Per-warehouse stock model — relevant for Shopify multi-location stores |
| `/businesses/:business/inventory-batch` | `src/services/inventory-batch/class.js` | Bulk upload paths (CSV today) — useful for one-shot product sync |
| `/businesses/:business/contacts` | `src/services/contacts/` | Customer/contact record — Shopify customer → Refrens contact mapping |
| `/businesses/:business/apps` | `src/services/business-apps/apps.service.js:26` | Per-business "installed apps" registry — could hold the Shopify install metadata |
| `/integrations` | `src/services/integrations/integrations.service.js:22` | Global integrations catalog. Currently used by `lms-Integrations`, no Shopify entry. |

### 3.3 Auth model

`src/authentication/AuthFactory.js:42-67` registers these strategies:
- `jwt`, `local`, `mail-token`, `http-basic` — end-user auth.
- `refresh-token` — refresh.
- `app-token` (JWTStrategy), `app-secret` (LocalStrategy), `app-iss-app-token` (AppJWTStrategy), `marika-token` (MarikaStrategy) — *app-to-app* auth. shopifyApp uses `app-secret` for the first exchange and `app-token` for refresh.
- `refrens-app` (RefrensAppStrategy) — HMAC sig verification for *inter-service* calls from other Refrens-owned backends. shopifyApp's `signRequest.js` is built for this strategy (header convention `X-Hmac-SHA256`, `X-Refrens-App-Req`, `X-Timestamp`). Per `RefrensAppStrategy.js` it has a `secretMap`/`allowedSources`/`timestampMaxAge` config — a per-source secret table.

So Refrens already has the two ingredients a clean bridge wants: a per-merchant bearer token (`app-secret → app-token`), and a system-to-system HMAC for back-channel calls. Today shopifyApp uses the bearer for everything except the lead create. We should keep both.

### 3.4 Event emission

`src/channels.js` is the default Feathers scaffold — publishes service events to authenticated SSE/WS connections, nothing more. **There is no outbound webhook surface in Serana today.** There are inbound webhook services (`razorpay`, `cashfree-webhook`, `tazapay-webhook`) and a generic `integrations` model, but no "Refrens → external system" event bus that shopifyApp could subscribe to. This is the single biggest *Serana-side* gap if we want Refrens → Shopify sync (e.g. Refrens invoice paid → Shopify order marked paid; Refrens stock change → Shopify inventory_level adjust).

### 3.5 Rate limits / multi-tenant

Serana is multi-tenant via `businesses/:business` route prefix. One Refrens user can own many businesses; one business has one URL key. There is no documented per-merchant rate limit, but Feathers runs behind whatever the infra fronting it imposes. **ASSUMPTION:** we treat Serana as "reasonably available, retry with backoff on 5xx and 429" — same as any internal HTTP call. Confirm with the Serana team.

---

## 4. Shopify REST capabilities (what matters for this integration)

All endpoints below carry the deprecation banner: *"The REST Admin API is a legacy API as of October 1, 2024. Starting April 1, 2025, all new public apps must be built exclusively with the GraphQL Admin API."* The migration risk is treated in §10.

Source URLs fetched on 2026-05-12:
- https://shopify.dev/docs/api/admin-rest/latest/resources/order
- https://shopify.dev/docs/api/admin-rest/latest/resources/product
- https://shopify.dev/docs/api/admin-rest/latest/resources/inventorylevel
- https://shopify.dev/docs/api/admin-rest/latest/resources/inventoryitem
- https://shopify.dev/docs/api/admin-rest/latest/resources/webhook
- https://shopify.dev/docs/apps/build/webhooks
- https://shopify.dev/docs/api/admin-rest/usage/rate-limits

### 4.1 Orders

- **Endpoints:** `GET /orders.json`, `GET /orders/{id}.json`, `POST /orders/{id}/cancel.json`, `POST .../close.json`, `POST .../open.json`, `PUT .../{id}.json`. No `POST .../orders.json` is needed for our flow (Shopify owns order creation).
- **Pagination:** cursor-based since 2019-07 (`page_info` cursors via `Link` header).
- **Access scope:** the past-60-day window is free with `read_orders`. Beyond 60 days requires the `read_all_orders` scope, which is a manual approval — **plan installs without it** and only sync forward.
- **Financial status:** `pending`, `authorized`, `partially_paid`, `paid`, `partially_refunded`, `refunded`, `voided`. We currently only branch on `paid` (`orders_created.js:27`).
- **Fulfillment status:** `fulfilled`, `null`, `partial`, `restocked`. We ignore this entirely today, which is fine for invoice/credit-note creation but means we cannot tell Refrens *which* line items shipped — relevant if Refrens stock decrement should follow shipment, not order.
- **Line items, taxes, addresses:** structure documented at the URL above. Notably each line has `tax_lines[]` (with `rate` already as a decimal), `discount_allocations[]` (allocations per discount), and `properties[]` (custom attributes from app extensions). The current `getItemsPayload` (`utils/utils.js:55`) handles `tax_lines` correctly but takes `taxes_included` from the order envelope, which is right.
- **Refunds:** `webhookRequestBody.refunds[]` on `orders/updated`. Each refund has `refund_line_items[]`, `order_adjustments[]` (shipping refunds live here), `transactions[]`. `orders_updated.js:33-40` already does this correctly but the math gets dense — see §6.4 for the recommended refactor.

### 4.2 Products + Variants

- **Endpoints:** `GET /products.json` (paginated), `GET /products/{id}.json`, `POST`, `PUT`, `DELETE`.
- **Each Variant carries:** `sku`, `barcode`, `inventory_item_id`, `inventory_quantity` (legacy — prefer InventoryLevel for current quantity), `inventory_management` (string: `shopify` or `null`), `option1/2/3`, `price`, `compare_at_price`, `weight`, `taxable`, etc.
- **Variant↔InventoryItem is 1:1.** SKU lives on the InventoryItem, not the Variant top level (though it's mirrored on the Variant).
- **Limit:** products have up to 100 variants by default; up to 2000 with the new product model (GraphQL only). For Refrens-as-stock-of-record, this is fine.

### 4.3 InventoryItem

- **Endpoints:** `GET /inventory_items.json?ids=...` (≤100 at a time), `GET /{id}.json`, `PUT /{id}.json`.
- **Fields we care about:** `sku`, `tracked` (boolean — must be `true` for InventoryLevel ops to mean anything), `cost`, `country_code_of_origin`, `harmonized_system_code`.
- **Critical:** Refrens' inventories are SKU-keyed; Shopify's are inventory_item_id-keyed. The mapping is `Shopify InventoryItem.sku ↔ Refrens inventory.sku`. We need a SKU-uniqueness invariant on both sides and a small mapping table for cases where SKU is missing (some merchants don't fill it).

### 4.4 InventoryLevel

- **Endpoints:**
  - `POST /inventory_levels/adjust.json` — delta adjust (best for incremental sync).
  - `POST /inventory_levels/set.json` — set absolute (good for initial sync / reconciliation).
  - `POST /inventory_levels/connect.json` — connect an item to a location before first adjust.
  - `GET /inventory_levels.json?inventory_item_ids=...&location_ids=...` — read.
  - `DELETE /inventory_levels.json` — disconnect.
- **Scope:** `inventory`.
- **One level per (inventory_item, location).** Multi-location stores will have N levels per item. Refrens has a `warehouses` model (`serana/docs/inventory.md` §8); the mapping Refrens-warehouse ↔ Shopify-location is the multi-tenant join we must store.

### 4.5 Webhooks

- **Topics we should subscribe to (and rationale):**

| Topic | Why | Frequency |
|---|---|---|
| `orders/create` | Today's invoice trigger | Per order |
| `orders/paid` | Today's payment trigger | Per payment |
| `orders/updated` | Today's refund + edit trigger | Hot — multiple per order, fan-out |
| `orders/cancelled` | Today's cancel trigger | Per cancel |
| `orders/fulfilled` | New — to fire Refrens stock decrement on shipment (more conservative than firing on order/create) | Per shipment |
| `refunds/create` | New — cleaner refund signal than parsing `orders/updated.refunds[]` | Per refund |
| `products/create` | Mirror new Shopify products into Refrens products (if merchant wants Shopify-as-source-of-truth) | Per product |
| `products/update` | Re-sync attributes (price, title) | Per edit |
| `products/delete` | Soft-flag in Refrens | Per delete |
| `inventory_levels/update` | Pull Shopify stock changes into Refrens (when Shopify-as-SoT) | Hot — every stock movement |
| `inventory_items/update` | Track cost / SKU changes | Per edit |
| `app/uninstalled` | Already subscribed | Per uninstall |
| `app_subscriptions/update` | Already subscribed | Per billing event |
| `customers/data_request` | **Mandatory** — currently NOT registered via webhooks API, only declared by URL in Partner Dashboard | Per GDPR request |
| `customers/redact` | **Mandatory** | Per request |
| `shop/redact` | **Mandatory** — fires 48h post-uninstall | Per uninstall |

- **HMAC verification.** Every delivery has `X-Shopify-Hmac-Sha256: base64(HMAC-SHA256(rawBody, SHOPIFY_API_SECRET))`. The `@shopify/shopify-api` SDK does this for us today via `shopify.webhooks.process` (`server/index.js:82`). Mandatory compliance topics — if we move them to be registered through the new `shopify.app.toml compliance_topics` block (api_version 2026-01), the SDK + Shopify CLI handle the wiring; we keep our `verifyHmac` middleware for any manually-wired endpoints.
- **Retry.** Per the Shopify developer changelog (per WebSearch on 2026-05-12), the retry policy was **updated** from the historical "19 attempts over 48h" to **8 attempts over 4 hours** with exponential backoff. After 8 consecutive failures the subscription is *auto-deleted*. This makes idempotency and fast 2xx response time more important than ever: a slow handler is one outage away from getting un-subscribed.
- **Duplicates.** Shopify emits the same webhook more than once in normal operation. Dedup using `X-Shopify-Event-Id`.
- **Ordering.** *Not guaranteed.* `orders/updated` can arrive before `orders/create`. We need to either tolerate out-of-order arrival or fetch the canonical order via REST when we see an unknown id.
- **Payload size.** Effectively bounded by what Shopify includes; for Orders this can be hundreds of KB on big orders. Current `WEBHOOK_BODY_LIMIT` env defaults to 2 MB (`server/index.js:77`) — reasonable.
- **Delivery options.** HTTPS endpoint (what we use today), Amazon EventBridge, Google Pub/Sub. The Shopify guidance now recommends Pub/Sub for high-volume; for our scale HTTPS is fine but worth knowing.

### 4.6 Rate limits

- REST Admin API uses the leaky-bucket: bucket size **40 per app per shop**, leak rate **2 req/s** for standard plans (Shopify Plus is 80/4). Over the limit → 429 with `Retry-After`. The current code has no rate-limit awareness at all; on a bulk product sync it would hit 429 immediately. The `@shopify/shopify-api` client throws `HttpThrottlingError` we can catch.

---

## 5. Gap analysis (per resource)

### 5.1 Orders

| Capability | Shopify offers | shopifyApp implements | Serana supports | Gap / Risk |
|---|---|---|---|---|
| New order → invoice | webhook `orders/create` | yes (`orders_created.js`) | `POST .../invoices` | Idempotency only via local `Order.createdOnRef` flag; no `X-Shopify-Event-Id` dedup; runs all 3 Refrens calls inline (create→payment→email) which can leave partial state on failure |
| Paid order → payment | webhook `orders/paid` | yes (`orders_paid.js`) | `POST .../invoices/{id}/payments` | `paymentMethod` hard-coded to `CASH`; no mapping from Shopify `payment_gateway_names[]`. No duplicate-payment guard if Shopify retries |
| Order edit → invoice edit | `orders/updated` carries items | no | Serana invoice PATCH exists | Currently we only process refunds out of `orders/updated`; merchant-side line-item edits are silently ignored |
| Refund → credit note | `orders/updated.refunds[]` and `refunds/create` | yes (partial, in `orders_updated.js`) | `POST .../creditnotes` | We're not subscribed to `refunds/create` (the cleaner topic). Math is correct but tangled. Idempotency is via the `Order.refundedItems` JSON blob — racy if two refunds happen in quick succession |
| Order cancel → invoice cancel | `orders/cancelled` | yes (`orders_cancelled.js`) | invoice PATCH | Works |
| Fulfillment (shipment) → stock decrement | `orders/fulfilled` | no | inventories adjustment via documents | If/when Refrens becomes stock-of-record, we want to decrement only on shipment, not on order — currently no path |
| Historical sync | `GET /orders.json?status=any` | no | n/a | First-install merchants get zero historical data into Refrens |
| Reconciliation | `GET /orders/{id}.json` | no | n/a | If we miss a webhook (e.g. our service was down) we have no catch-up job |

### 5.2 Products + Variants

| Capability | Shopify offers | shopifyApp implements | Serana supports | Gap / Risk |
|---|---|---|---|---|
| Product create/update mirror | `products/*` webhooks | no | `POST .../products`, `POST .../inventories` | No path at all. If merchant adds a product in Shopify, Refrens never learns about it. Refrens-side invoice creation succeeds only because Refrens auto-creates inventories on first invoice line — but the product entity is missing |
| Refrens-side product → Shopify | n/a (write to Shopify via `POST /products.json`) | no | `products` service exists | If a merchant primarily manages catalog in Refrens, no way to push to Shopify |
| Variant resolution by SKU | `GET /variants.json?sku=...` (not standard — needs query) | no | `inventories?sku=...` | No SKU lookup at all. When we want to act on a Shopify line item, we have no way to map back to a Refrens inventory item. Today we just embed the line title in the invoice |

### 5.3 Inventory

| Capability | Shopify offers | shopifyApp implements | Serana supports | Gap / Risk |
|---|---|---|---|---|
| Pull Shopify stock → Refrens | `inventory_levels/update` webhook + REST GET | no | `inventories.patch` with stock adjustment | No path |
| Push Refrens stock → Shopify | n/a (we call Shopify) | no | Need an outbound event from Serana | **Biggest Serana-side gap**: there's no outbound notification on stock change |
| Multi-location | inventory levels are per location | no | warehouses model | Mapping Shopify location ↔ Refrens warehouse doesn't exist; would need a per-shop config |
| Initial sync on install | `GET /products.json` + `GET /inventory_levels.json` | no | bulk inventory create (`inventory-batch`) | No bootstrap path |
| Stock reservation on cart/checkout | n/a in our scope (would be Checkout/Cart APIs) | no | BLOCK transactions exist (PI/SO) | Out of scope — keep ignoring |

### 5.4 Webhooks

| Capability | Shopify offers | shopifyApp implements | Serana supports | Gap / Risk |
|---|---|---|---|---|
| HMAC verify | yes | yes via SDK | n/a | Fine |
| Idempotency (dedup by event id) | exposes `X-Shopify-Event-Id` | **no** | n/a | **Big risk** — we silently re-process duplicate refunds and may double-issue credit notes when our handler is slow |
| Fast-ack + async work | recommended | **no** — inline | n/a | If Refrens 5xx's and we wait 30s, Shopify retries and we may double-issue. Need queue |
| Replay | n/a — manual via REST GET | no | n/a | If we miss webhooks (e.g. outage), no catch-up |
| Mandatory compliance | required for App Store listing | partial (URLs exist; not subscribed via `shopify.app.toml`) | n/a | App review risk |
| Observability | `X-Shopify-Triggered-At`, `X-Shopify-Webhook-Id` | partial (`console.log`) | n/a | No structured event log; hard to debug a customer report of "my invoice didn't sync" |

---

## 6. Target architecture

### 6.1 High-level diagram

```
┌──────────────────┐         ┌───────────────────────────────────┐         ┌──────────────────┐
│                  │         │                                   │         │                  │
│ Shopify          │         │  shopifyApp  (Node + Express)     │         │  Serana          │
│ Admin store      │ ──────► │  ────────────────────────────────  │ ──────► │  /businesses/... │
│                  │  HTTPS  │  /webhooks/:topic                 │   HTTPS │                  │
│                  │  HMAC   │    ├─ verify HMAC                 │  Bearer │  invoices        │
│                  │         │    ├─ dedup by event_id           │   +     │  creditnotes     │
│                  │         │    ├─ persist raw event           │ HMAC for│  payments        │
│                  │         │    └─ ACK 200 (<200ms)            │ system  │  inventories     │
│                  │         │                                   │ calls   │  products        │
│                  │         │  Worker (BullMQ / Cloud Tasks)    │         │  business-apps   │
│                  │         │    ├─ load event                  │         │                  │
│                  │         │    ├─ map → Refrens payload       │ ◄──────┤  outbound events │
│                  │ ◄────── │    ├─ call Serana (with retry)    │  Pub/Sub│  (NEW — see §9)  │
│                  │  REST/  │    └─ record attempt + outcome    │ or HTTP │                  │
│                  │  GQL    │                                   │ webhook │                  │
└──────────────────┘         │  /reconcile  (cron + manual)      │         └──────────────────┘
                             │    └─ scan Shopify for missing    │
                             │       events + re-enqueue         │
                             │                                   │
                             │  Postgres                         │
                             │  ├─ Store     (per-shop config)   │
                             │  ├─ Mapping   (sku/loc, etc)      │
                             │  ├─ Event     (raw + status)      │
                             │  └─ Job log   (attempts, errors)  │
                             └───────────────────────────────────┘
```

### 6.2 Data flows

#### (a) New Shopify order → Refrens invoice

```
1. Shopify           POST /webhooks/orders_create  (HMAC, X-Shopify-Event-Id: <uuid>)
2. shopifyApp        verify HMAC (via SDK)
3. shopifyApp        SELECT event WHERE event_id = $1; if exists → 200 (idempotent ack)
4. shopifyApp        INSERT event(event_id, shop, topic, raw_body, received_at, status=PENDING)
5. shopifyApp        enqueue job(event.id)
6. shopifyApp        respond 200
                     ─────────── async ───────────
7. Worker            load event; load Store; refresh refrensToken if expired (existing logic)
8. Worker            map line items via getItemsPayload; resolve gstState; build invoicePayload
9. Worker            POST /businesses/:urlKey/invoices with Idempotency-Key: <event_id>
                     5xx or 429 → exponential backoff retry (up to N); 4xx → mark FAILED + alert
10. Worker           on 2xx: write Order row with invoiceId + invoiceNumber
11. Worker           if order is paid → enqueue payment job (separate job for retry granularity)
12. Worker           if autoSendInvoice → enqueue email job
13. Worker           mark event status=DONE; record attempts JSON
```

Note: **Idempotency-Key** should be propagated to Serana too — see §9, ask Serana team to honor it on `POST /invoices`. As a fallback, shopifyApp computes a deterministic external ref (`shopify:{shop}:{order_id}`) and Serana de-dupes on that.

#### (b) Shopify product / inventory change → Refrens

```
products/create or products/update:
  Shopify → shopifyApp /webhooks/products_create
  Worker:
    for each variant:
      sku = variant.sku
      lookup Refrens inventory by sku (GET /businesses/:urlKey/inventories?sku=X)
        not found → POST /inventories with { sku, name, isStockManaged: true, source: 'SHOPIFY' }
        found     → PATCH /inventories/:id with attribute diff (name, price hint, etc.)
      record Mapping(shopify_variant_id ↔ refrens_inventory_id) in local DB

inventory_levels/update:
  Shopify → shopifyApp /webhooks/inventory_levels_update
  Worker:
    payload = { inventory_item_id, location_id, available }
    lookup variant by inventory_item_id (cached locally from products webhook)
    lookup sku → Refrens inventory id via Mapping
    lookup Refrens warehouse by mapping (shopify_location_id ↔ refrens_warehouse_id)
    POST /businesses/:urlKey/inventory-adjustments  (NEW endpoint — see §9)
      with { sku, warehouse, finalStock: available, reason: 'SHOPIFY_SYNC', source: 'SHOPIFY' }
    Serana converts to an UPDATE inventory transaction internally
```

ASSUMPTION: Serana exposes (or will expose) a "set absolute stock for SKU at warehouse" endpoint that's idempotent on `(sku, warehouse, sourceEventId)`. Today the bulk-upload class supports a `finalStock` field (`inventory-batch/class.js` `transactionUploadDoc` per `inventory.md` §6.3) but only via bulk CSV. A REST endpoint that wraps the same logic for a single SKU is the missing piece.

#### (c) Refrens invoice → Shopify

For an invoice created *in Refrens* (the merchant uses Refrens as their billing UI), do we want to mirror it back to Shopify? Probably no — Shopify owns the order lifecycle. The one exception is **marking the Shopify order paid** when a Refrens payment is recorded for a Shopify-originated invoice. This requires a Serana outbound event:

```
Serana: invoice-payments after.create hook
  if invoice.shopifyOrderNumber exists:
    emit OutboundEvent('invoice.payment.recorded', { shopifyOrderNumber, amount, ... })

Bridge subscribes to OutboundEvent or polls /outbound-events :
  POST <shop>.myshopify.com/admin/api/<v>/orders/<id>/transactions.json
    with { kind: 'capture', amount, currency }
  OR (simpler) call GraphQL orderMarkAsPaid mutation
```

This is **net-new on the Serana side**; today there is no outbound mechanism. Flag in §9.

#### (d) Refrens inventory change → Shopify

Same pattern as (c):

```
Serana: inventories after.patch hook (or inventory-transactions after.create)
  if Mapping(refrens_inventory_id → shopify_inventory_item_id) exists for this shop:
    emit OutboundEvent('inventory.stock.changed', { sku, warehouse, stockInHand })

Bridge:
  POST /admin/api/<v>/inventory_levels/set.json
    with { inventory_item_id, location_id, available: stockInHand }
```

This must respect Shopify's leaky-bucket rate limit; throttle inside the worker.

### 6.3 Webhook + reliability design

**Webhook ingress (HTTP handler):**
1. HMAC-verify (SDK handles).
2. Read `X-Shopify-Event-Id`, `X-Shopify-Webhook-Id`, `X-Shopify-Topic`, `X-Shopify-Shop-Domain`, `X-Shopify-Triggered-At`.
3. `INSERT ... ON CONFLICT (event_id) DO NOTHING` into `WebhookEvent` table. Conflict = duplicate = ACK and return.
4. Enqueue background job with `eventId`.
5. Respond 200 with body `{ ok: true }`. P99 target: 200ms.

**Worker:**
1. Pull job; `SELECT FOR UPDATE` the `WebhookEvent`.
2. Route by topic; call typed handler.
3. Each handler is **a pure mapper + a single side-effect**. Side effects use an HTTP client with built-in retries on `5xx`/`429` and a circuit breaker for prolonged Serana outages.
4. After handler: `UPDATE WebhookEvent SET status, attempts = attempts || $1, last_error`.

**Dead letter:** events that fail N retries go to `status=DEAD`. A `/debug/dead-letter` page (already a debug-routes pattern) lets staff replay one.

**Replay job:** a daily cron that, for each active shop, fetches `GET /orders.json?updated_at_min=<24h ago>` and reconciles against our local Order rows. Anything missing → synthesize a synthetic event and enqueue.

**Compliance webhooks:** declare in `shopify.app.toml`:

```toml
[webhooks]
api_version = "2026-01"

  [[webhooks.subscriptions]]
  topics = ["orders/create", "orders/paid", "orders/updated", "orders/cancelled",
            "orders/fulfilled", "refunds/create",
            "products/create", "products/update", "products/delete",
            "inventory_levels/update", "inventory_items/update",
            "app/uninstalled", "app_subscriptions/update"]
  uri = "/webhooks"

  [[webhooks.subscriptions]]
  compliance_topics = ["customers/data_request", "customers/redact", "shop/redact"]
  uri = "/webhooks/compliance"
```

This is the canonical way as of api_version 2026-01 — see the Shopify privacy-law-compliance docs. We drop the manual Partner Dashboard config currently documented in `SETUP.md:52-55`.

### 6.4 Auth & session — proposed

- **Shopify ↔ shopifyApp:** keep as is (online + offline OAuth, Prisma-backed sessions, Cryptr-encrypted). Move secrets out of `.env` into a real secret store (AWS SM / Doppler / Vault — depending on Refrens infra).
- **shopifyApp ↔ Serana:** *retire the user-pasted API key UX.* Replace with one of:
  1. **Best:** an OAuth-like dance during Shopify install. The user clicks "Connect Refrens", lands on `refrens.com/oauth/authorize?...&state=<shop>`, picks a business, redirected back with a code, shopifyApp swaps the code for a per-(shop,business) bearer + refresh token. Requires Serana to add an OAuth-ish authorize page. **ASK SERANA TEAM**.
  2. **Acceptable interim:** keep the API key paste but (a) encrypt at rest using the same `Cryptr` as sessions and (b) make the keys never leave Serana → they're sent to shopifyApp only as a one-time bootstrap that yields a long-lived refresh token. shopifyApp then forgets the key.
- **System-to-system (e.g. bulk back-channel):** keep `RefrensAppStrategy` with a `shopify` source. shopifyApp signs with a single shared secret; Serana verifies. Already wired for `/leads`; extend to any new bridge endpoints that don't fit the per-merchant bearer model.

### 6.5 Multi-tenant model

```
Shopify shop "x.myshopify.com"     1 ─── 1     Store row (shopifyApp Postgres)
                                                 └── refrens_business_id (urlKey)
                                                 └── refrens refresh token
                                                 └── shopify offline access token

Store                              1 ─── *     Mapping rows
                                                 ├── kind: 'variant'  → (shopify_variant_id, refrens_inventory_id, sku)
                                                 ├── kind: 'location' → (shopify_location_id, refrens_warehouse_id)
                                                 └── kind: 'order'    → (shopify_order_id, refrens_invoice_id)
```

One Shopify shop maps to exactly one Refrens business. (ASSUMPTION: this is the product intent; if a merchant runs multiple Shopify storefronts off one Refrens business, they install the app once per shop and pick the same business — no schema change needed.)

### 6.6 Error handling, retries, observability

- **HTTP retries:** 5xx + 429 + network errors → retry with exponential backoff (50ms, 200ms, 1s, 5s, 30s, 5m), max 5 attempts, then DLQ.
- **4xx:** *no auto-retry.* Map to a `FAILED` status and surface in the merchant-visible "Sync status" dashboard.
- **Sentry:** capture every DLQ entry with full event payload as an attachment (or a presigned-url'd S3 blob).
- **Logs:** structured JSON, one log line per (shop, event_id, topic, refrens_call, http_status, duration_ms). Pipe to whatever Refrens uses (Loki / Datadog / OpenSearch).
- **Metrics:** counters `shopify_webhook_received{topic,shop}`, `shopify_webhook_acked{topic,shop}`, `refrens_call_total{endpoint,status}`, `refrens_call_duration_seconds{endpoint}`. Alert when 4xx rate > 5% or DLQ depth > 50.
- **Trace:** `X-Shopify-Webhook-Id` flows into Serana as a request header (e.g. `X-Source-Event-Id`) for cross-system trace.

### 6.7 Rate-limit handling

Centralize Shopify-side outbound calls behind a per-shop token bucket: 2 tokens/sec, max 40. The `@shopify/shopify-api` SDK already throws `HttpThrottlingError` with `retryAfter` — catch in the worker and reschedule the job.

### 6.8 Data reconciliation job for drift

A nightly cron per shop:
1. `GET /admin/api/<v>/orders.json?updated_at_min=<yesterday>&status=any&financial_status=any`.
2. For each, compare against our local Order row. Anything we don't have → enqueue a synthetic `orders/create`.
3. For inventory: `GET /inventory_levels.json?location_ids=...` for each location, compare against Serana `inventories._find()`. Drift > threshold → log + (if `auto_reconcile=true` config) push a `set` to Shopify.

This catches: missed webhooks, our DLQ entries we never replayed, Shopify's "duplicate-not-quite-duplicate" deliveries where we accepted only one.

### 6.9 Compliance webhooks (GDPR mandatory three)

| Topic | Required behavior | Implementation |
|---|---|---|
| `customers/data_request` | Within 30 days return all PII held about that customer | Today: stub. Target: build an `/exports` job that hits Serana to find any invoice with that customer email/phone and emit a JSON dump. Email it to the shop owner; Refrens itself emails the customer. |
| `customers/redact` | Within 30 days delete or anonymize | Target: hit Serana `clients` / `contacts` services and request anonymization for matching email/phone. ASK SERANA TEAM if there's a soft-delete + anonymize op already. |
| `shop/redact` | Within 30 days delete all merchant data, fires 48h post-uninstall | Today: deletes Store. Target: delete Store + all Mapping + all WebhookEvent rows older than retention; also send a Serana call to flag the business's Shopify-source records (don't auto-delete Refrens invoices — those are the merchant's books). |

### 6.10 REST→GraphQL hedge

Build new code on the GraphQL Admin client. Wrap REST calls behind a `shopifyClient.orders.get(...)`-style facade so a future swap is a single-class change. Any new webhooks subscribe via GraphQL `webhookSubscriptionCreate` (or `shopify.app.toml`, which is GraphQL underneath). Existing REST calls in the current handlers can stay; mark each with `// TODO(graphql)`.

---

## 7. Webhook + reliability design (consolidated)

This is the single most important change. Pulling §6.3 + §6.6 + §6.7 + §6.8 into a checklist:

1. **`WebhookEvent` table** with unique constraint on `event_id`. Columns: `id`, `event_id`, `shop`, `topic`, `webhook_id`, `triggered_at`, `received_at`, `raw_body` (or pointer), `status` (PENDING/PROCESSING/DONE/FAILED/DEAD), `attempts JSONB`, `last_error`, `refrens_response_summary JSONB`.
2. **HTTP handler** at `/webhooks/:topic` and `/webhooks/compliance/:topic`:
   - Verify HMAC.
   - `INSERT ... ON CONFLICT DO NOTHING` returning `id`. If no row inserted → ACK 200.
   - Enqueue job(`event.id`).
   - Respond 200 within 200ms.
3. **Worker** (BullMQ on Redis is the path of least resistance and matches Serana's choice per `serana/CLAUDE.md`):
   - Topic-router → typed handler.
   - Typed handler is pure: `(event) => RefrensCall[]`.
   - Calls executed by a single HTTP client with per-shop token bucket + exponential retry.
   - On success: `status=DONE`. On 4xx: `status=FAILED`. On exhausted retries: `status=DEAD`.
4. **Manual replay** UI at `/debug/dead-letter` (extends current debugRoutes pattern).
5. **Cron replay** daily; gated per shop by config.
6. **Compliance topics** subscribed via `shopify.app.toml compliance_topics` block, not Partner Dashboard URL config.

---

## 8. Prioritized change list for shopifyApp

### P0 — must do before any new feature

1. **Webhook persistence + dedup** by `X-Shopify-Event-Id`. Even before adding a queue, just persisting the event id and skipping duplicates fixes the most common bug class. Cost: ~1d. Touches: `server/index.js`, new `prisma` model, `webhooks/*.js`.
2. **Move webhook work off the request thread.** Add BullMQ + Redis. All current handlers become jobs. Cost: ~3d.
3. **Encrypt `refrensApiKey` / `refrensSecretKey`** at rest. Use the existing `Cryptr` instance. Cost: <½d. Touches: `prisma/schema.prisma`, `storeSettings.js`, a one-off migration.
4. **Fix `app_uninstalled.js`** — set `isActive=false`, keep all other fields. Don't drop tokens. Cost: <½d.
5. **Register compliance webhooks via `shopify.app.toml`** and implement them. Cost: ~1d (counting actual `customers/redact` logic).
6. **Fix latent broken references** — `Setup` import (`GlobalRoutes.jsx:31`), `onboardingFlow` model (`app_proxy/onboarding.js:9`), `appInstallationId` field (`billing.js:56`). Either add to schema or remove the calls. Cost: ~½d.
7. **Sentry on all envs** (drop the `production/staging` gate) with `dev` tagged. Cost: 5min.

### P1 — needed for an end-to-end revamp

8. **Idempotency on Refrens calls.** Send `Idempotency-Key: <event_id>` header and have Serana honor it (ASK SERANA). Until Serana supports it, dedup client-side by `Order.<shop>:<order_id>:<topic>:<event_id>` lookup. Cost: ~2d.
9. **Reconciliation job** (`GET /orders.json` daily). Cost: ~2d.
10. **Replace the API key paste UX** with an OAuth-style hop to Refrens. Cost: ~1w end-to-end; depends on Serana shipping an authorize page. Big UX win.
11. **Hard-code-to-`CASH` payment method** — read Shopify `payment_gateway_names[]` and map. Cost: ~½d.
12. **Move refund handling to `refunds/create` topic** instead of parsing `orders/updated`. Cost: ~1d.
13. **Front-end: build a real "Sync Status" page** that lists recent events + their state. Cost: ~3d.
14. **Drop @apollo/client + raviger** and align on a single state/router story (react-query is already in). Cost: ~1d cleanup.
15. **Test fixtures** — capture sample webhook payloads (use `tmp/` finally) and a Jest harness. Cost: ~1d.

### P2 — the actual revamp scope (products + inventory)

16. **Product mirror (Shopify → Refrens).** Subscribe to `products/create`, `products/update`, `products/delete`. Cost: ~1w. Depends on Serana inventories SKU-lookup endpoint being reliable.
17. **Inventory pull (Shopify → Refrens).** Subscribe to `inventory_levels/update`. Cost: ~1w. Depends on a Serana "set absolute stock" idempotent endpoint (ASK SERANA).
18. **Inventory push (Refrens → Shopify).** Requires a Serana outbound event mechanism (ASK SERANA). Cost: ~2w including Serana work.
19. **Initial bulk sync on connect.** Walk `products` + `inventory_levels` once per location. Cost: ~3d.
20. **Multi-location mapping UI** — Shopify location ↔ Refrens warehouse table editor in `Settings.jsx`. Cost: ~2d.
21. **GraphQL migration.** Convert all REST resource usage to GraphQL Admin clients, behind a facade. Cost: ~2w. Driver: any new feature should be GraphQL from day one.

### P3 — nice-to-have

22. Theme extension (per `TODO.md:3`).
23. Onboarding email flow (the commented-out `sendOnboardingEmails`).
24. Per-shop "auto-reconcile on drift" toggle.
25. Sentry replay attachments for failed events.

---

## 9. Ask list for the Serana team

Tag these in Asana — each is a small RFC-class question.

1. **OAuth-style authorize for app installs.** Can Serana expose `/oauth/authorize?app=shopify&state=<shop>&redirect_uri=...` that returns a per-(user, business) code, then `POST /oauth/token` to exchange for a long-lived bearer + refresh? Today the only path is "user pastes API key", which is a security and UX wart.
2. **Idempotency on writes.** Will Serana honor `Idempotency-Key` headers on `POST /invoices`, `POST .../payments`, `POST .../creditnotes` such that a second call with the same key returns the original 201 result (not a duplicate)? Today shopifyApp builds its own dedup via the `Order` table.
3. **Inventory "set absolute" endpoint.** Today `inventory-batch/class.js` `transactionUploadDoc` supports `finalStock` over CSV. We need the single-SKU equivalent as a REST endpoint, idempotent on `(sku, warehouse, externalEventId)`. Roughly: `POST /businesses/:business/inventory-adjustments` `{ sku, warehouse, finalStock, reason, source, externalEventId }`.
4. **Outbound event surface.** What's the right Refrens-side mechanism for "send me a webhook when invoice X is paid" and "send me a webhook when SKU Y stock changes in business Z"? Options: native FeathersJS event publishing pipeline + a new `outbound-webhooks` service that subscribes to internal events and POSTs to registered URLs; or a Pub/Sub topic the bridge subscribes to; or a poll-based `/businesses/:business/outbound-events?since=<cursor>`. Refrens has no precedent today; we should pick one and document it as an ADR (Serana's `docs/decisions/` pattern).
5. **GDPR `customers/redact` mapping.** Is there an existing op for "anonymize this contact's PII across all documents for business X"? If not, how should we surface this in the contacts/clients services?
6. **Variant ↔ inventory mapping table.** Does Refrens have a notion of "external system mapping" on the inventory schema (talos)? If not, where should the bridge store `shopify_variant_id ↔ refrens_inventory_id` — locally in shopifyApp Postgres (current default), or as an embedded `externalRefs[]` array on the Refrens inventory document? Embedded is cleaner for downstream reporting but a Talos schema change.
7. **Rate-limit posture from Serana.** Any docs on per-business / per-app rate limits we should respect when doing a bulk initial sync? Confirm 429 behavior.
8. **`shopifyOrderNumber` field.** Today shopifyApp pushes this on invoice creation (`orders_created.js:78`); is it stored, indexed, queryable? We'd like to `GET /invoices?shopifyOrderNumber=...` for the reconciliation job.

---

## 10. REST→GraphQL migration risk

**The facts.**
- Shopify declared REST Admin legacy on **2024-10-01** ([docs banner verified 2026-05-12]).
- **2025-02-01:** all *public* apps using deprecated GraphQL fields or REST products/variants endpoints must have migrated to the new GraphQL product APIs (re: variants > 100 etc.).
- **2025-04-01:** all *new* public apps must be GraphQL-only.
- **2025-04-01:** custom apps on deprecated GraphQL fields must migrate.
- **No public sunset date for existing REST users yet.** Per Shopify changelog and developer community as of mid-2025, REST endpoints continue to work; Shopify will announce a date later.

**The risk for Refrens (private app today, public app aspiration).**
- The current app is publicly listed (per its README; "Refrens App" is in the Shopify App Store). Listing renewal at the next major review will trigger a check for compliance webhooks and likely a nudge on GraphQL.
- The pinned REST resource bundle (`server/shopify.js:5` — `require(@shopify/shopify-api/rest/admin/${SHOPIFY_API_VERSION})`) means every API version bump is a code change.
- Any feature we add that wasn't in REST (e.g. the new product model with > 100 variants) is GraphQL-only.

**Hedge.**
- New code: GraphQL. Behind a thin facade (`shopifyClient.products.get(id) → graphql mutation`) so we can swap implementations.
- Existing code: leave on REST until we have a reason to touch. Tag each REST call with a `// TODO(graphql)` comment so a future sweep is easy.
- Webhook subscription via `shopify.app.toml` (which is GraphQL underneath) for all new topics — see §6.3.
- Build the prototype (§11) on GraphQL from day one.

---

## 11. Prototype scoping (smallest end-to-end demo)

**The bet:** prove the *bridge architecture* works on the simplest interesting flow — **a new Shopify order generates a Refrens invoice through the new persisted-event, async-worker pipeline.** Not the inventory loop, not the full product mirror — just the order path, re-built right.

**In scope:**
- One Shopify dev store, one Refrens dev business.
- A new minimal `shopifyApp v2` (or a feature-flagged branch of the existing) with:
  - `shopify.app.toml`-declared webhook subscription for `orders/create` only.
  - Webhook handler that HMAC-verifies, persists a `WebhookEvent` row, enqueues a BullMQ job, and returns 200 in <200ms.
  - Worker that maps the event → Refrens invoice payload, posts to `/businesses/:urlKey/invoices` with `Idempotency-Key: <event_id>`, persists the result.
  - A simple `/sync-status` Polaris page listing the last 50 events for the merchant with their state.
- Force a duplicate delivery (Shopify CLI `shopify webhook trigger`) and prove no duplicate invoice is created.
- Force a Serana 500 (mock it) and prove the event sits in `PENDING/FAILED → retried`, and after 5 failures lands in `DEAD` with a Sentry tag.
- Force a Serana timeout and prove Shopify gets its 200 within 200ms regardless.

**Minimum endpoints/webhooks:**
- Shopify: `orders/create` webhook only.
- Refrens: existing `POST /authentication`, `POST /businesses/:business/invoices`. No new Serana endpoints required.

**Complexity:** ~1 engineer × 1 week. The Polaris page is ~½ day; everything else is Node + Postgres + Redis plumbing that exists in dozens of references. The hard part is wiring `shopify.app.toml` for webhook declaration and getting BullMQ + Prisma migrations clean.

**Why this prototype:** it proves the part of the architecture that *every other change depends on* — the persisted-event, idempotent, retry-aware worker pipeline. Once that's real, adding `orders/paid`, `orders/updated`, `refunds/create`, `products/*`, `inventory_levels/update` is just more topic handlers.

---

## 12. Assumptions made during research

1. The cloned `shopifyApp` repo at `/Users/apple/Refrens/Andromeda-temp/research-shopify-revamp/shopifyApp` is the in-production code; the `tmp/` and `extensions/` placeholders suggest there was no recent meaningful work outside the order pipeline.
2. The Refrens "appId / appSecret / urlKey" the user pastes maps 1:1 to a Refrens business via the urlKey, and Serana's `app-secret` strategy returns a JWT scoped to that business. (Confirmed by reading `storeSettings.js` + `RefrensAppStrategy.js` + `AppJWTStrategy.js`.)
3. Serana's invoice service accepts arbitrary pass-through fields (notably `shopifyOrderNumber`), so a new `externalEventId` field should be similarly accepted without schema work — but I haven't grepped the document schema in talos to confirm. Flagged in §9.
4. Refrens is currently INR/GST-centric — the GST state map (`utils/utils.js:1`) is hard-coded and the invoice creation drops a `gstState` field. International merchants (where `billing_address.country_code !== 'IN'`) currently get `gstState: undefined`. That works but should be tested.
5. The "8 retries over 4 hours" webhook retry policy is per the current Shopify developer changelog as of 2026-05-12 (per WebSearch). The historical "19 attempts over 48 hours" number from older blog posts is no longer accurate.
6. There is no second Refrens service emitting events I should know about — Serana is the system of record. Per `serana/CLAUDE.md`, all stock writes go through the inventories/inventory-transactions chain, and there is no outbound event publisher today.
7. The Refrens product team's intent is to position Shopify as one of several "sales channels" feeding a Refrens-owned books/inventory hub. If the intent is the opposite (Refrens supplements Shopify), the inventory push direction in §6.2(d) reverses.

---

## 13. Open questions

1. **Stock-of-record direction.** Is Refrens or Shopify authoritative for stock? If Refrens, the inventory_levels webhook is informational only and we never push back. If Shopify, the Refrens-side stock updates from non-Shopify sources (manual adjustments, expenditures) must push back to Shopify. The architecture supports either; the merchant needs a per-shop config toggle, and a UI to set it. Today no such toggle exists.
2. **One Refrens business = N Shopify stores?** The current schema implies 1:1. If a merchant runs multiple storefronts in the same legal entity (e.g. US and EU stores) and wants a single Refrens books, we need a `Mapping` per shop. The current model handles this naturally because the `Store` table is keyed by shop domain.
3. **Should we support B2B / custom price lists?** Out of scope per the prompt, but worth noting: Shopify B2B uses GraphQL exclusively and would force the migration sooner.
4. **Are international tax rates okay?** Today the GST-state lookup silently falls through for non-Indian addresses. Confirm with merchants who sell across borders.
5. **Currency conversion.** `orders_created.js:25` passes `currency` to Serana but does not convert. If the Refrens business currency differs from the order currency, we need a conversion-rate hop. Serana has a `conversion-rate` service (`src/services/conversion-rate/`) — confirm shopifyApp should call it.
6. **Theme extension.** What's the actual goal? `TODO.md` mentions it but `extensions/theme-extension` is empty. Skip until the goal is clear.
7. **Plan / pricing implications.** The current `subscriptionRegular.js` uses `EVERY_30_DAYS` $9.99 and Enterprise $99. Out of revamp scope but worth a product-side sanity check before any re-listing.
8. **What's the Refrens-side stock decrement timing preference?** On `orders/create` (immediate, matches Shopify cart-checkout semantics) or on `orders/fulfilled` (matches accounting "when did inventory actually leave")? Probably the latter, but ask the team.

---

*End of blueprint.*
