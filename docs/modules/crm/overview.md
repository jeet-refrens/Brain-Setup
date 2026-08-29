# CRM — Overview

> Grounded in the live `talos` schemas (`clients.js`, `contacts.ts`, `contactRelations.ts`,
> `contactActivities.ts`, `leads.js`, `leadPipelineHistory.js`, `vendorLeads.js`, `workflows.js`,
> `workflowitems.js`, `salesActivities.js`, `integrations.js`) and `fence` enums, read via the
> GitHub API, verified **2026-08-15**. Business logic lives in `serana`; forms in `lydia`.
> See [schema.md](schema.md) for field detail and [integrations.md](integrations.md) for
> third-party lead sources.

## Purpose

Manage the people and organisations a business sells to and buys from, and the sales process that
turns an enquiry into a document. Two halves that meet in the middle:

- **Lead management (LMS)** — inbound enquiries move through configurable pipeline stages until they
  convert or are lost.
- **Client/vendor master** — the billing-side records that documents and accounting attach to.

## The three party models — read this first

The most common source of confusion in this module. There are **three** distinct things:

| Model | What it represents | Created by |
|---|---|---|
| **`clients`** | An **organisation** a business bills or buys from. Carries billing address, GSTIN/VAT/TRN, payment terms, balances, and the Saturn `ledgerId`. | Invoicing, uploads, dashboard, lead conversion, API |
| **`contacts`** | An **individual person** — name, email(s), phone(s), social, gov IDs. Business-scoped, deduplicated and mergeable. | Contact book, lead capture |
| **`contactRelations`** | The **link** between a contact and a client, with `department`, `role`, `isPrimary`, `isActive` | Explicit linking |

A `clients` row is *not* a person: it has `contactPersonName`, `phone` and `email` fields inline for
convenience, but the real person records are `contacts` joined through `contactRelations`.
One client can have many contacts, exactly one of which is `isPrimary`.

**Role flags, not types.** A client row carries independent booleans — `isClient`, `isVendor`,
`isBilledClient`, `isSelf` — so the same organisation can be both customer and supplier. There is
no "customer vs vendor" enum; check the flags. (`isSelf` marks a client created for the business
itself, e.g. for warehouse-to-warehouse delivery challans.) `clientType` is a separate axis:
`INDIVIDUAL` by default.

## Core entities

- **`clients`** — organisation master. Also holds `bankAccounts[]` (vendor payout details, kept
  here by an explicit past decision rather than a separate collection), `shippingDetails[]`
  (multiple ship-to addresses), `balance{}` (cached per-document-type totals), `retentionMetrics`,
  `customFields`/`vendorFields`, `ledgerId` + `previousLedgers[]`.
- **`contacts`** — person master: `salutation`, `firstName`, `lastName`, `email`, `phone`, `social`,
  `address`, `govIdentities`, `avatar`, plus merge machinery (`isMerged`, `mergedTo`, `mergedBy`)
  and an optional `refrensUserId` link to a real Refrens user.
- **`contactRelations`** — contact ↔ client link (`isPrimary`, `department`, `role`, `isActive`).
- **`contactActivities`** — audit trail on a contact: `CREATE`, `UPDATE`, `DELETE`, `MERGE`,
  `LINKED`, `UNLINKED`, against entity types `clients`, `leads`, `vendorLeads`, `invoices`.
- **`leads`** — the enquiry/opportunity record (the largest schema in the module, ~940 lines).
  Carries `status`, `pipeline`, `customer`/`contact` blocks, `budget`, `subject`, `details`,
  `questions`, `vendors[]`, `comments`, `changeHistory`, `utm`, `attachments`, `followUpDate`,
  `duplicate`, and links out to `client`, `quotation`, `proforma`, `invoices[]`, `project`.
- **`leadPipelineHistory`** — one doc per lead recording every stage entry/exit with durations and
  decay state (deliberately embedded as an array, not a per-transition collection — the schema
  comment explains why and when to revisit).
- **`salesActivities`** — per-lead activity events (`activity`, `changeFrom`, `changeTo`,
  `assignee`, `renewal`) used for funnel reporting.
- **`vendorLeads`** — the vendor-side equivalent of leads.
- **`workflows` / `workflowitems` / `workflowitemactivites`** — a generic approval-workflow engine
  (see below).
- **`integrations`** — third-party lead sources and connectors.
- Supporting: `notes`, `tasklist`, `meetings`, `calls`, `outboundCalls`, `messageTemplates`,
  `inboundMessages`, `forms`, `leadcomments`.

## Lead pipelines

Pipelines are **business-level configuration**, not their own collection: they live at
`businessConfigurations.lms.pipelines[]`. Each `Pipeline` has `name`, `description`,
`leadStages[]`, `customFields[]`, `isPrimary`, `isArchived` + `archivedMeta` (which records what
happens to the leads in it on archive).

Each `LeadStage` carries:

- `name`, `labels[]`, `reasons[]`
- `state` — the underlying lead status the stage maps to (`NEW`, `OPEN`, `CLOSED`, `DROPPED`,
  `REJECTED`)
- `closure` — a number read as **sales probability %** in reports
- `decayThreshold` (always stored in **hours**; `decayThresholdDisplayUnit` is `days`/`hours` for
  display only)
- `_id` — a nanoid **string**, not an ObjectId

So a lead has both a coarse `status` (the enum) and a fine-grained stage (`_id` within its
pipeline). The default template (`fence/leads/pipeline.json`) is "Sales Pipeline":
Open (10%) → Contacted (20%) → Proposal Sent (50%) → Deal Done (100%, `CLOSED`) →
Lost (0%, `DROPPED`) / Not Serviceable (0%, `REJECTED`).

**Lead duplication** is configurable per business (`lms.duplication`): `enabled`, `crossPipeline`
(check across all pipelines vs only the lead's own), and `factors[]` (at least one required when
enabled).

## Approval workflows

A separate, generic engine from lead pipelines — used to gate **documents**, not leads.

- **`workflows`** — a named, typed workflow with ordered `stages[]`. Type comes from
  `fence/workflows/config.json`: `INVOICE`, `PROFORMAINV`, `QUOTATION`, `SALESORDER`,
  `PURCHASEORDER`, `EXPENDITURE`, `VENDOR_LEADS`. Each stage has `approvers[]`,
  `approvalRequiredFrom` (`ANYONE`/`EVERYONE`), `reasons[]`, and `policies[]` (permission strings
  applied while a document sits in that stage). Workflow-level `superApprovers[]`,
  `dueDateConfig`, `reminders` and `escalations` (frequency arrays + recipients from
  `Assignee`/`Approvers`/`SuperApprover`).
- **`workflowitems`** — one live instance: `sourceDocument`, `currentStage`, `currentAssignee`,
  `status` (`OPEN` → `COMPLETED` / `CLOSED`), `dueDate`, plus per-item `reminders`/`escalations`
  dunning schedules.
- **`workflowitemactivites`** — the audit trail: `internalNote`, `addedRemarks`, `userRemarks`,
  `statusUpdate`, `stageUpdate`, `reassigned`, `addedToWorkflow`, `dueDateChange`.

Status **labels are business-configurable** (`configurations.statusLabels`) — `OPEN` defaults to
"In Process", `COMPLETED` to "Approved", `CLOSED` to "Rejected". Never hard-code the display text.

## Key user flows

1. **Capture a lead** — manually, via a public form (`forms`), via bulk upload, or via an
   integration webhook (IndiaMART, Facebook/Meta, TradeIndia). Source is recorded on the lead.
2. **Work the pipeline** — assign, comment, log activities, move stages. Each move writes a
   `leadPipelineHistory` stage entry and a `salesActivities` row.
3. **Convert** — generate a quotation/proforma/invoice from the lead; the lead links to the created
   documents and (usually) to a `clients` record.
4. **Maintain the contact book** — create contacts, link them to clients with a role, merge
   duplicates (`mergedTo`), archive.
5. **Route documents through approval** — attach a document to a workflow; it becomes a
   `workflowitem` that moves stage by stage with reminders and escalations.
6. **Client servicing** — statements, outstanding and ageing reports (see
   [../accounting/reports.md](../accounting/reports.md)).

## Status lifecycles

- **Lead** (`leads.status`, default `NEW`, from `fence/leads/status.json`):
  `NEW` ("New") → `OPEN` ("Open") → `CLOSED` ("Deal Done") / `DROPPED` ("Lost") /
  `REJECTED` ("Not Serviceable"). Note the labels differ from the keys — display the label.
- **Lead decay** (`leadPipelineHistory.decayStatus`): `On Track` → `Needs Attention` → `Stalled`.
  Driven by the stage's `decayThreshold`; a decay can be marked `justifiedDecay` with
  `delayRemarks`.
- **Workflow item** (`workflowitems.status`): `OPEN` → `COMPLETED` / `CLOSED`.
- **Contact**: active → `isArchived` → `isRemoved` (with `removeReason`) → `isHardRemoved`;
  or absorbed via `isMerged` + `mergedTo`.
- **Client**: `isArchived`, then `isHardRemoved`. Clients are archived, not deleted, in normal flows.

## Known edge cases

- **`clients.balance` is a cache, not the books.** For authoritative balances read Saturn — see
  [../accounting/overview.md](../accounting/overview.md).
- **`clients.ledgerId` may be re-pointed**; `previousLedgers[]` retains the history. Don't assume
  one client ↔ one ledger forever.
- **Client/vendor is a flag combination**, not a type — `isClient` and `isVendor` can both be true.
- **Contacts merge, clients don't.** `contacts` has full merge machinery (`isMerged`/`mergedTo`);
  `clients` does not. Deduplicating organisations is a different, unsolved problem.
- **Lead stage `_id`s are nanoid strings**, and stages live inside a business config document — a
  stage reference is not a resolvable ObjectId ref.
- **`decayThreshold` is always hours in storage.** Reading it as days is a common bug.
- **`activities` ≠ `salesActivities`.** `activities` is the social/network feed (portfolio, follows,
  badges); CRM sales events are in `salesActivities` and `contactActivities`.
- **Vendor bank accounts live on `clients.bankAccounts[]`**, not in `bankAccounts` — an explicit
  past decision made during the Cashfree payouts work, flagged in the schema comment as
  migratable later.
- **Two "workflow" concepts.** The `workflows` approval engine here is unrelated to the
  Workflow & Documents module's document lifecycle — see
  [../workflow-documents/document-workflow.md](../workflow-documents/document-workflow.md).
- **India-specific fields sit alongside international ones** on the same client record: `gstin`,
  `gstState`, `stateCode`, `panNumber` next to `vatNumber`, `trnNumber`, `sstNumber`, `tinNumber`,
  `additionalIds[]` and a configurable `vatLabel`. Don't assume GST.
