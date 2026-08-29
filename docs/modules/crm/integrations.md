# CRM — Integrations

> Grounded in `talos/src/integrations.js` and `fence/external-integrations/`, `fence/leads/`,
> verified **2026-08-15**. Connector logic lives in `serana`; the Shopify bridge is its own repo.

All third-party connections for a business live in a single **`integrations`** collection, one row
per business per `integrationType`.

## The integration record

| Field | Meaning |
|---|---|
| `business` (req) | Owning business |
| `integrationType` (req, enum) | Which provider — see table below |
| `pipeline` | Which lead pipeline inbound leads land in. **Required** for every lead-source integration; not required for AISENSY, COMPLYANCE, CASHFREE-MERCHANT and GOOGLE-CALENDAR (the `integrationsWithoutPipeline` list) |
| `country` | Country scoping for the connection |
| `accessKey` | Provider credential/key |
| `lastFetch`, `lastFetchId`, `lastFetchStatus` | Polling state. `lastFetchStatus` is the union of the IndiaMART and FB/Meta response-status enums. For the IndiaMART cron, `lastFetch` is the window **end** time |
| `backfill` | Historical-import state, statuses from `fence/leads/indiamart/backfillStatuses.json` |
| per-provider blocks | `aisensy`, `tradeIndia`, `complyance`, `facebookMeta`, `cashfreeMerchant`, `googleCalendar` |
| `isActive`, `isPaused`, `isRemoved`, `version`, `params`, `createdBy` | Lifecycle |

Note the tri-state lifecycle: an integration can be **inactive** (`isActive: false`), **paused**
(`isPaused: true`) or **removed** (`isRemoved: true`) — these are independent flags, not one status.

## Providers

`fence/external-integrations/integrationTypes.json`:

| Key | Value | What it does |
|---|---|---|
| `indiaMart` | `INDIAMART` | IndiaMART lead marketplace (India B2B) |
| `indiaMart-webhook` | `INDIAMART-WEBHOOK` | Push delivery of IndiaMART leads |
| `indiaMart-backfill` | `INDIAMART-BACKFILL` | Historical import of IndiaMART leads |
| `fb-meta` | `FB-META` | Facebook / Meta Lead Ads |
| `tradeIndia` | `TRADE-INDIA` | TradeIndia marketplace (autofetch) |
| `aisensy` | `AISENSY` | WhatsApp Business messaging |
| `complyance` | `COMPLYANCE` | E-invoicing / tax compliance |
| `cashfree-merchant` | `CASHFREE-MERCHANT` | Payments/payouts merchant onboarding — tracks `productMinKycStatus` |
| `google-calendar` | `GOOGLE-CALENDAR` | Calendar sync for meetings |

**Lead-source integrations** (IndiaMART, FB/Meta, TradeIndia) all write into `leads`, stamping
`source` from `fence/leads/creation-source.json`:

- `INDIAMART_WEBHOOK` (push) and `INDIAMART_CRON` (poll/backfill)
- `FB_META_WEBHOOK`
- `TRADEINDIA_AUTOFETCH`
- `BULKUPLOAD` (system, not an integration — CSV import)

FB/Meta lead forms map extra fields through
`fence/leads/fbMeta/leadSecondaryFieldsMap.json`; IndiaMART sub-sources come from
`fence/leads/indiamart/sources.json` and are validated against `leads.source`.

## Not in this collection

- **Shopify** — a standalone app (`refrens/shopifyApp`) with its own Postgres/Prisma store, not an
  `integrations` row. It currently only does *Shopify order → Refrens invoice*; there is no product
  or inventory bridge and no outbound-event mechanism on the Refrens side. See
  [../../../features/shopify-revamp/SUMMARY.md](../../../features/shopify-revamp/SUMMARY.md) and
  `blueprint.md` in that folder for the full gap analysis.
- **Zoho** — appears only as a `clients.source` value (`ZOHO`), i.e. an import provenance marker,
  not a live connector.
- **Marika** (subscriptions) — an internal Refrens product, surfaced on the client record as
  `marikaCustomer` and as a `clients.source` value.
- **Public lead forms** (`forms` collection) and the embeddable contact widget (`venus`) — inbound
  lead capture, but first-party, not third-party integrations.

## Things to check before building here

- **Does the provider need a `pipeline`?** If it creates leads, yes — and the record will fail
  validation without one.
- **Push vs poll.** IndiaMART has both a webhook type and a cron/backfill type as *separate*
  `integrationType` values on the same provider. Don't treat "IndiaMART" as one integration.
- **Duplicate handling** is a business-level lead setting (`lms.duplication`), not a per-integration
  one — an integration that floods duplicates is governed by that config. See
  [schema.md](schema.md).
- **Reliability.** There is no shared retry/DLQ layer described in these schemas; `lastFetchStatus`
  + `backfill` state is the whole error surface. The Shopify blueprint's reliability
  recommendations (persisted event log, dedup key, worker + DLQ) apply here too and are not yet
  built.

## Source of truth

- **`refrens/talos`** — `src/integrations.js`, `src/forms.js`, `src/inboundMessages.ts`,
  `src/messageTemplates.js`.
- **`refrens/fence`** — `external-integrations/integrationTypes.json`,
  `external-integrations/aisensy/`, `leads/creation-source.json`,
  `leads/indiamart/` (`sources.json`, `responseStatuses.json`, `backfillStatuses.json`),
  `leads/fbMeta/` (`responseStatuses.json`, `leadSecondaryFieldsMap.json`), `leads/tradeIndia/`,
  `cashfreeMerchant/productMinKycStatus.json`.
- **`refrens/serana`** — integration services and lead-ingestion crons/webhooks.
- **`refrens/shopifyApp`** — the Shopify bridge (separate architecture).
- **`refrens/venus`** — embeddable contact-form widget.
