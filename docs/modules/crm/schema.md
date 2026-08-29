# CRM — Schema

## Summary

> Curated from the live `talos` models and `fence` enums, verified **2026-08-15**. `leads.js` is
> large (~940 lines); the table below is a curated slice. Use **Source of truth** for exact and
> complete fields.

### Entities & key fields

| Entity (model) | Key fields (curated) | Notes |
|---|---|---|
| **`clients`** (organisation master) | `name`, `contactPersonName`, `alias`, `uniqueKey`, `logo`, `domain`, `business`→`businesses`, `profile`→`businesses`, `phone`, `email`, `dueInDays`, address block (`street`, `city`, `district`, `building`, `pincode`, `state`, `stateCode`, `country`), tax ids (`gstin`, `gstState`, `vatNumber`, `trnNumber`, `sstNumber`, `tinNumber`, `vatLabel`, `taxPayerType`, `additionalIds[]`, `panNumber` via `panSchema`), `clientType`(default `INDIVIDUAL`), `source`(enum), `isClient`/`isVendor`/`isBilledClient`/`isSelf`/`isArchived`/`isHardRemoved`, `balance{...}`, `shippingDetails[]`, `bankAccounts[]`, `cc[]`, `files[]`, `customFields`, `customFieldsOld[]`, `vendorFields`, `ledgerId`, `previousLedgers[]`, `defaultPaymentBank`→`paymentaccounts`, `defaultPaymentVPA`→`paymentaccounts`, `industry`, `entity`→`entities`, `smartAccount`, `locale`, `shareId`, `avgPayingDate`, `lastCommunication`, `feedbackRequested`, `retentionMetrics{...}`, `marikaCustomer`, `csvUploadId` | One row per organisation. Role is a **flag combination**, not a type. `ledgerId` is the Saturn accounting link. |
| ↳ `clients.balance` | `invoice`, `proforma`, `creditNote`, `paymentReceipt`, `debitNote`, `salesOrder`, `invoicePayment`, `proformaPayment`, `expenditure`, `expenditurePayment`, `creditConsumed`, `currency` | **Cache** of per-document-type totals in one currency. Not the books. |
| ↳ `clients.shippingDetails[]` | `name`, `street`, `city`, `district`, `building`, `pincode`, `state`, `stateCode`, `country`, `gstState`, `gstin`, `sstNumber`, `tinNumber`, `taxId`, `taxPayerType`, `additionalIds[]`, `customHeaders[]`, `archived` | Multiple ship-to addresses per client. |
| ↳ `clients.retentionMetrics` | `docActivity{lastInvoiceDate, lastProformaInvoiceDate, lastSalesOrderDate, lastQuotationDate, lastPaymentDate, lastDocumentDate}`, `status{state, lastStatusUpdate}` | `state` enum from `fence/clients/retentionConfig.json`. |
| ↳ `clients.bankAccounts[]` | `bankSchema` fields + `isPrimary`, `isRemoved` | Vendor payout details — deliberately stored here, not in `bankAccounts`. |
| **`contacts`** (person master) | `uniqueKey`, `business`(req), `salutation`(enum, nullable), `firstName`, `lastName`, `avatar`, `country`, `social`, `email`, `phone`, `address{... gstState}`, `govIdentities`, `vendorFields`, `creator`→`users`, `refrensUserId`→`users`, `isMerged`/`mergedTo`→`contacts`/`mergedBy`, `isArchived`, `isRemoved`/`removedAt`/`removeReason`/`removedBy`, `isHardRemoved`/`hardRemovedAt`, `params` | Business-scoped. Full merge machinery — a merged contact keeps a `mergedTo` pointer rather than vanishing. |
| **`contactRelations`** | `contact`→`contacts`(req), `client`→`clients`(req), `business`(req), `creator`→`users`(req), `isPrimary`(default false), `department`, `role`, `isActive`(default true), `isRemoved`/`removedAt`/`removeReason`, `isHardRemoved`, `vendorFields`, `params` | The contact↔client join. **One primary contact per client.** |
| **`contactActivities`** | `business`, `contact`→`contacts`, `user`→`users`, `actionType`(enum), entity block with `entityType`(enum) | Audit trail. `actionType`: `CREATE`·`UPDATE`·`DELETE`·`MERGE`·`LINKED`·`UNLINKED`. `entityType`: `clients`·`leads`·`vendorLeads`·`invoices`. |
| **`leads`** | `status`(enum, default `NEW`), `source`, `adminSource`, `origin`, `decayStatus`, `referrer`/`referrerBusiness`, `business`, `client`→`clients`, `clientBusiness`, `clientUser`, `primaryContact`, `otherContacts`, `linkedBusinesses`, `quotation`, `proforma`, `invoices[]`, `project`, `product`, `pricePlan`, `parentRequirement`→`leads`, `vendors[]{status, lead, comment}`, `customer`, `contact`, `budget{amount, currency}`, `subject`, `details`, `questions`, `commission{feeAmount, feeType}`, `subscription`, `recurrence`, `comments`, `changeHistory`, `lastUserAction`, `duplicate`, `category`, `industries`, `keywords`, `clientLocation`, `attachments`, `utm`, `startTimeEstimate`, `followUpDate`, `lastClientUpdateDate`, `readExpiry`/`isRead`, `shareId`, `creator`, `metadata`, `dates`(Map→Date), `privateFields`, `vendorFields`, `params`, `ref{...}`(immutable original), `external`, `isLegacy`, `isRemoved`/`reason`/`removedAt`, `isHardRemoved`, `elasticCreatedAt`/`elasticUpdatedAt` | The enquiry/opportunity. `ref` is a frozen copy of the original inbound lead. `dates` is a free-form Map of milestone timestamps. Elastic-synced. |
| ↳ `leads.vendors[].status` | `AUTO_MATCH`, `INTERNAL`(default), `SHORTLISTED`, `VENDOR_INTERESTED`, `VENDOR_NOINTEREST`, `REFFFER_REJECTED`(sic), `SUGGESTED`, `CONSIDERED`, `ACCEPTED`, `REJECTED`, `DECLINED` | Vendor-matching sub-state on a lead. |
| **`leadPipelineHistory`** (`leadpipelinehistories`) | `lead`→`leads`(req), `pipeline`(ObjectId, req), `business`(req), `currentStageId`(String), `currentStageEnteredAt`, `stageHistory[]`, `totalDecays`(int), `decayStatus`(`On Track`/`Needs Attention`/`Stalled`), `decayCheckedAt` | **One doc per lead**, history embedded as an array — the schema carries an explicit comment on why (atomic single-write transitions) and when to revisit. |
| ↳ `stageHistory[]` | `stageId`, `stageName`, `enteredAt`, `exitedAt`, `durationHours`, `decayThresholdHours`, `decayed`, `justifiedDecay`, `delayRemarks`, `remarksAddedBy`, `exitSource`(`manual`/`auto`/null), `entryBy`/`exitBy`/`entryAssignee`/`exitAssignee`→`users` | One entry per stage occupancy. |
| **`salesActivities`** | `business`(req), `leadId`→`leads`(req), `clientBusiness`, `pipeline`, `assignee`→`users`, `user`→`users`, `activity`(String, req), `changeFrom`, `changeTo`, `renewal`(bool), `leadCreatedAt`(req), `ogDoc`(Mixed) | Funnel-reporting event stream. `activity` is a free String, not an enum. |
| **`vendorLeads`** | vendor-side lead record (`name`, `orgName`, `email`, `phone`, `source`, `vendor`, `vendorType`, `country`, …) | Drives the `VENDOR_LEADS` workflow type. |
| **`workflows`** | `name`(req), `description`, `type`(req, enum from `fence/workflows/config.json`), `stages[]`, `configurations.statusLabels{OPEN, COMPLETED, CLOSED}`, `workflowPolicies[]`, `reasons`(Map→`{label, isArchived}`), `superApprovers[]`→`users`, `dueDateConfig{enabled, frequency}`, `reminders`/`escalations{enabled, frequency[], recipients[]}`, `business`(req), `createdBy`(req), `isRemoved`/`removedAt`, `isHardRemoved`/`hardRemovedAt` | `frequency` on `dueDateConfig` is **hours**. `recipients`: `Assignee`·`Approvers`·`SuperApprover`. Policy arrays are validated as duplicate-free. |
| ↳ `workflows.stages[]` | `name`(req), `approvalRequiredFrom`(`ANYONE` default /`EVERYONE`), `approvers[]`→`users`, `config{color, isSystem}`, `reasons[]`, `policies[]`, `isArchived` | |
| **`workflowitems`** | `business`(req), `workflow`→`workflows`(req), `sourceDocument`(ObjectId, req — **no `ref`**), `currentStage`(ObjectId, req), `currentAssignee`→`users`(req), `status`(default `OPEN`), `dueDate`, `reminders`/`escalations`(dunning), `createdBy`/`updatedBy`, `isRemoved`, `isHardRemoved` | `sourceDocument` is untyped — resolve it via the parent workflow's `type`. |
| ↳ dunning schedule | `isEnabled`, `dunning[]{when(req), remindDate, isCompleted, recipients[], params}` | `when` is an offset; recipients same enum as workflow. |
| **`workflowitemactivites`** | activity log per workflow item, typed by `fence/workflowActivities/workflowActivitiesTypes.json` | Types: `internalNote`, `addedRemarks`, `userRemarks`, `statusUpdate`, `stageUpdate`, `reassigned`, `addedToWorkflow`, `dueDateChange`. Note the misspelled collection name (`activites`). |
| **`integrations`** | `business`(req), `integrationType`(req, enum), `pipeline`(required unless the type is pipeline-less), `country`, `lastFetchStatus`, `lastFetch`, `lastFetchId`, `accessKey`, `backfill`, per-provider blocks (`aisensy`, `tradeIndia`, `complyance`, `facebookMeta`, `cashfreeMerchant`, `googleCalendar`), `createdBy`, `version`, `isActive`, `isPaused`, `isRemoved`, `params` | See [integrations.md](integrations.md). |
| **`businessConfigurations.lms`** | `tags[]`, `adminSource[]`, `reasons[]`, `pipelines[]`, `businessFormCount`, `duplication{enabled, crossPipeline, factors[]}` | **Pipelines are config, not a collection.** |
| ↳ `Pipeline` | `name`(req), `description`, `leadStages[]`, `customFields[]`, `isPrimary`, `isArchived`, `archivedMeta{createdAt, reason, leadsAction}` | |
| ↳ `LeadStage` | `_id`(**nanoid String**, 18 chars), `name`, `state`(default `OPEN`, lead-status enum), `labels[]`, `reasons[]`, `closure`(Number — sales probability %), `decayThreshold`(**hours**), `decayThresholdDisplayUnit`(`days`/`hours`), `isArchived` | Defined in `talos/src/helpers/LeadHelpers.js`. |
| Supporting | `notes`, `tasklist`, `meetings`, `calls`, `outboundCalls`, `messageTemplates`, `inboundMessages`, `forms`, `leadcomments` | Activity/communication surface around leads and clients. |

### Enums (exact, from `fence`)

- **`leads/status.json`** — key → label: `NEW`→"New", `OPEN`→"Open", `CLOSED`→"Deal Done",
  `DROPPED`→"Lost", `REJECTED`→"Not Serviceable". **Labels differ from keys — display the label.**
- **`leads/customer-status.json`** — `OPEN`→"Open", `CLOSED`→"Deal Done", `DROPPED`→"Lost",
  `REJECTED`→"Junk (Not Serviceable)".
- **`leads/types.json`** — `HIRING` · `CUSTOMER` · `VENDOR` · `OTHER`.
- **`leads/creation-source.json`** — `INDIAMART.WEBHOOK`→`INDIAMART_WEBHOOK`,
  `INDIAMART.BACKFILL`→`INDIAMART_CRON`, `FBMETA.WEBHOOK`→`FB_META_WEBHOOK`,
  `TRADEINDIA.AUTOFETCH`→`TRADEINDIA_AUTOFETCH`, `SYSTEM.BULKUPLOAD`→`BULKUPLOAD`.
- **`leads/reasons.json`** — keyed reason list (`rs-freshlead`, `rs-notReachable`,
  `rs-wrongContactDetails`, `rs-messageEmailDropped`, `rs-followUpLater`, `rs-clientWentCold`,
  `rs-notInCharge`, `rs-positiveReply`, `rs-negativeReply`, `rs-waitingForReply`,
  `rs-expectationsMismatch`, …). Stage `reasons[]` holds these keys.
- **`clients.source`** (inline enum): `INVOICE`(default), `CLIENT_DASHBOARD`, `CLIENT_UPLOAD`,
  `ZOHO`, `INVOICE_BULK_UPLOAD`, `DASHBOARD`, `LEADFORM`, `PORTFOLIO`, `MARIKA`, `LEADAPI`, `API`.
- **`businesses/clientTypes.json`** — `clients.clientType`, default `INDIVIDUAL`.
- **`contacts/activityActionTypes.json`** — `CREATE`, `UPDATE`, `DELETE`, `MERGE`, `LINKED`,
  `UNLINKED`. **`contacts/activityEntityTypes.json`** — `["clients","leads","vendorLeads","invoices"]`.
- **`contacts/salutations.json`** — allowed salutations (null permitted).
- **`workflows/config.json`** — workflow `type` values: `INVOICE`, `PROFORMAINV`, `QUOTATION`,
  `SALESORDER`, `PURCHASEORDER`, `EXPENDITURE`, `VENDOR_LEADS`. Each entry also carries `service`,
  `prefix`, `docLabel`, `selectItemFields[]` and a `defaultValues` template.
- **`workflows/approvalRequired.json`** — `EVERYONE` · `ANYONE`.
- **`workflowitems/status.json`** — `OPEN`("In Progress") · `COMPLETED`("Completed", user label
  "Approve") · `CLOSED`. Each carries display colors — the enum doubles as a UI config.
- **`external-integrations/integrationTypes.json`** — `INDIAMART`, `INDIAMART-BACKFILL`,
  `INDIAMART-WEBHOOK`, `FB-META`, `TRADE-INDIA`, `AISENSY`, `COMPLYANCE`, `CASHFREE-MERCHANT`,
  `GOOGLE-CALENDAR`.
- **`clients/retentionConfig.json`** — `retentionMetrics.status.state` values.
- **`leads/duplicationFactors.json`** — allowed `lms.duplication.factors[]`.

### Relationships

```
contacts ──N── contactRelations ──N── clients ──1── ledgerId ──► saturn ledgers
   │                                     │
   └── contactActivities                 ├── invoices / paymentrecords  (Workflow & Documents,
                                         │                              Accounting)
                                         └── balance{} (cache)

leads ──1── leadPipelineHistory (stageHistory[])
  │  └──N── salesActivities
  ├──► client → clients
  ├──► quotation / proforma / invoices[] → invoices
  └──► pipeline → businessConfigurations.lms.pipelines[]._id
             └── leadStages[]._id  (nanoid string)

workflows ──N── workflowitems ──N── workflowitemactivites
                     └──► sourceDocument (untyped ObjectId; resolve via workflows.type)

integrations ──► pipeline (which pipeline inbound leads land in)
```

- `clients` 1—N `contactRelations` N—1 `contacts` (many-to-many with role metadata).
- `contacts.mergedTo` → `contacts` (self-referential merge chain).
- `leads.parentRequirement` → `leads` (a lead spawned from a requirement).
- `leads.client` → `clients` is set on conversion; before that a lead holds raw
  `customer`/`contact` blocks instead.
- `workflowitems.sourceDocument` → `invoices` (or `vendorLeads`) depending on `workflows.type`.

## Source of truth

`gh` was not installed at last verification; contents were read via the GitHub REST API
(reference `GITHUB_PAT` **by name only**). Or run `/sync-schema crm`.

- **`refrens/talos`** — `src/clients.js`, `contacts.ts`, `contactRelations.ts`,
  `contactActivities.ts`, `leads.js`, `leadPipelineHistory.js`, `vendorLeads.js`,
  `salesActivities.js`, `workflows.js`, `workflowitems.js`, `workflowitemactivites.js`,
  `integrations.js`, `forms.js`, `notes.js`, `tasklist.js`, `meetings.js`, `calls.js`,
  `outboundCalls.ts`, `inboundMessages.ts`, `messageTemplates.js`;
  `src/helpers/LeadHelpers.js` (`LeadStage`, `LeadReason`, `AdminSource`),
  `src/helpers/CustomFields.js`, `src/helpers/workflow.ts`, `src/helpers/panBank.js`;
  `src/businessConfigurations.ts` (`lms` block ~line 378, `Pipeline` ~line 174).
- **`refrens/fence`** — `leads/` (`status.json`, `customer-status.json`, `types.json`,
  `pipeline.json`, `creation-source.json`, `admin-source.json`, `reasons.json`,
  `duplicationFactors.json`, `acv-multipliers.json`, `csvheaders.json`, `indiamart/`, `fbMeta/`,
  `tradeIndia/`), `contacts/` (`activityActionTypes.json`, `activityEntityTypes.json`,
  `salutations.json`, `contactAuditFieldMapping.json`, `csvheaders.json`), `clients/retentionConfig.json`,
  `workflows/config.json`, `workflows/approvalRequired.json`, `workflowitems/status.json`,
  `workflowActivities/workflowActivitiesTypes.json`,
  `external-integrations/integrationTypes.json`, `businesses/clientTypes.json`.
- **`refrens/serana`** — services `clients`, `contacts`, `contact-relations`,
  `contact-activities`, `leads`, `leads-batch`, `lead-pipeline-history`, `lead-reports`,
  `lead-duplicate`, `lead-followup-email`, `lead-whatsapp`, `leadcomments`, `vendor-leads`,
  `refrensleads`, `workflows`, `workflowitems`, `workflowitems-activities`,
  `client-dashboard`, `client-batch`, `client-ledger`, `client-outstanding-report`,
  `client-ageing-report`. **`refrens/lydia`** — CRM forms and pipeline UI.
- **Fetch pattern** (no `gh`; PAT referenced by name, never printed):
  ```bash
  curl -s -H "Authorization: Bearer $GITHUB_PAT" -H "Accept: application/vnd.github.raw" \
    "https://api.github.com/repos/refrens/talos/contents/src/leads.js"
  ```
