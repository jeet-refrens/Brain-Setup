# PLG function map

What Refrens can do, grouped by the side of the business it serves. This is the
working list for setting **expected function sets per nature of business**.

Status: **draft for review with sales.** Last updated 20 August 2026.

## Why functions and not features

A business that does Quotation, then Proforma, then Invoice is doing **one** thing:
selling. A business that does Invoice and Expense is doing **two**: money in and money
out.

So we count **sides of the business**, not document types. Counting document types
punishes a business that has a short sales process, which is a choice, not a gap.

## The eight functions

| Function | What it means |
|---|---|
| **Sell** | Getting paid for what you provide. Quotation, proforma, invoice, sales order, delivery challan. |
| **Buy** | What you spend. Expenses, purchases, purchase orders. |
| **Money** | Where the money sits and moves. Payments recorded, payment accounts, payment gateway. |
| **Stock** | What you hold. Items, warehouses, batches, serials, adjustments. |
| **CRM** | Who you sell to, before they buy. Leads, pipelines, forms, follow-ups. |
| **Books** | The accounts. Ledgers, vouchers, reconciliation, financial reports, GST. |
| **Team** | More than one person. Extra users, roles, approvals. |
| **Ownership** | Making it yours. Templates, own sending domain, branding, custom fields. |

**Ownership is not a side of the business.** It does not widen coverage. It raises the
cost of leaving. Treat it as a **candidate second axis**, tracked and tested, not part
of the spine until it earns a place.

## The map

`tracked` means it is in `businessacquisitions.featureUsage`. `measurable` means we can
count it today from another field. `none` means we cannot see it.

### Sell

| Function | Signal | State |
|---|---|---|
| Invoice creation | `featureUsage.invoices` | tracked |
| Quotation creation | `featureUsage.quotations` | tracked |
| Proforma invoice | `featureUsage.proformaInvoices` | tracked |
| Sales order | `featureUsage.salesOrders` | tracked |
| Delivery challan | `featureUsage.deliveryChallans` | tracked |
| Convert quote to invoice | `featureUsage.convertQuotationToInvoice` | tracked |
| Share invoice | `featureUsage.shareInvoice` | tracked |
| One-click document acceptance | `featureUsage.oneClickDocumentAcceptance` | tracked |
| e-Invoicing | `featureUsage.eInvoicing` | tracked |
| Invoices API | `featureUsage.invoicesApi` | tracked |
| **Recurring invoices** | `invoices.recurringInvoice.nextDate`, indexed | **measurable, add** |
| **Credit note** | `accounting.CREDITNOTE.TOTAL` | **measurable, add** |
| **Debit note** | `accounting.DEBITNOTE.TOTAL` | **measurable, add** |
| **Payment reminders / dunning** | `invoices.reminders.dunningEnabled`, indexed | **measurable, add** |
| **Bulk upload / import** | `accounting.ALL.BULKUPLOAD` | **measurable, add** |
| Document e-signature | `documentsignaturerequests` | measurable, unchecked |
| RFI / RFQ | - | none |
| Package items | - | none |

### Buy

| Function | Signal | State |
|---|---|---|
| Expense creation | **use `invoices.isExpenditure: true`** | measurable |
| Purchases | `featureUsage.purchases` | tracked |
| Purchase orders | `featureUsage.purchaseOrders` | tracked |
| Reimbursement OCR | `featureUsage.reimbursementOcr` | tracked |
| Vendor forms | - | none |

> `featureUsage.expenses` **under-reports**. It showed 354 businesses where direct
> counting showed 1,117. The feature is new and the tracker is behind. Count from
> `isExpenditure` until that is fixed.

### Money

| Function | Signal | State |
|---|---|---|
| Payment recorded on invoice | `featureUsage.paymentReceipts` | tracked |
| Payment account added | `featureUsage.paymentAccount` | tracked |
| Bank account added | `featureUsage.bankAccountsAdded` | tracked, **subset of payment account** |
| Advance payment receipt | `featureUsage.advancePaymentReceipts` | tracked |
| Payout receipt | `featureUsage.payoutReceipts` | tracked |
| Payment gateway integration | `integrations` CASHFREE-MERCHANT | measurable, unchecked |

> **Name collision.** "Payment recorded on invoice" is **not** the `PAYMENTRECEIPT`
> document type. Only 5 businesses in a 63,605 cohort ever made a `PAYMENTRECEIPT`
> document, while `featureUsage.paymentReceipts` shows thousands. Do not build a metric
> until the two are named apart.
>
> A payment account may be a bank, an employee, a credit card or UPI. A bank account is
> one kind of payment account. **Count payment account for the Money function. Do not
> count both.**

### Stock

| Function | Signal | State |
|---|---|---|
| Add item | `featureUsage.addItem` | tracked |
| Real-time inventory sync | `featureUsage.realTimeInventorySync` | tracked |
| Multiple stock locations | `featureUsage.multipleStockLocations` | tracked (warehouses **enabled**) |
| Batch tracking | `featureUsage.batchwiseTracking` | tracked |
| Manual adjustment | `featureUsage.manualAdjustment` | tracked |
| **A warehouse actually created** | `accounting.ALL.WAREHOUSES` | **measurable, add** |
| Serial tracking | - | flag coming |
| Stock transfer | `inventorytransactions` docType `TRANSFERSTOCK` | measurable, unchecked |
| Opening stock, reorder points | - | none |

> The business-level `manageInventory` switch is **not** a usable signal. It is being
> defaulted to true to cut friction, so it will be true for everyone. Measure Stock by
> real movements and real items instead.

### CRM

| Function | Signal | State |
|---|---|---|
| Lead creation | `featureUsage.leads` | tracked |
| Multiple pipelines | `featureUsage.multiplePipelines` | tracked |
| Embedded lead forms | `featureUsage.embeddedForms` | tracked |
| Create quote from lead | `featureUsage.createQuotationFromLead` | tracked |
| Lead forms in use | `accounting.ALL.LEADFORMS` | measurable |
| **Follow-ups / sales activity** | `salesactivities`, `contactactivities`, `calls` | **measurable, add** |
| **Contacts (people)** | `contacts`, `contactRelations` | **measurable, add** |
| Notes / tasks | `notes`, `tasklists` | measurable, unchecked |
| Calendar meetings | `meetings`, `integrations` GOOGLE-CALENDAR | measurable, unchecked |
| IndiaMART / TradeIndia / Meta | `integrations.integrationType` | measurable, unchecked |
| WhatsApp (Aisensy) | `integrations` AISENSY | measurable, unchecked |

> **Do not use `featureUsage.client` as a CRM signal.** A client record is created
> automatically when an invoice is created, so it measures invoicing, not CRM. Its ~85%
> adoption is an artefact.

### Books

| Function | Signal | State |
|---|---|---|
| Real-time books sync | `featureUsage.realTimeBooksSync` | tracked |
| Bank statement reconciliation | `saturn.reconciliations` | measurable, unchecked |
| GSTR-2B reconciliation | `gstr2bentries` | measurable, unchecked |
| Custom reports | `accounting.ALL.CUSTOM_REPORTS` | measurable |
| **Financial reports (P&L, Balance Sheet)** | `featuresUnlocked.accountingReports` | **add** |
| **Ledgers / chart of accounts** | `saturn.ledgers`, `accountgroups` | **measurable, add** |
| **Manual voucher / journal entry** | `saturn.vouchers` | **measurable, add** |
| **GSTR-1 filing** | `gstfilings`, `gstreturns` | **measurable, add** |
| **e-Way bill** | - | **add, India** |
| **Multi-currency** | `invoices.conversionRates` | **add, 40% of users** |
| TDS / TCS | - | none |

### Team

| Function | Signal | State |
|---|---|---|
| More than one user | `featureUsage.userCount` (true when users > 1) | tracked |
| Approval workflows set up | `featureUsage.approvalWorkflows` | tracked |
| Approval workflow used | `featureUsage.approvalWorkflowUsage` | tracked |
| Workflows in use | `accounting.ALL.WORKFLOWS` | measurable |
| Roles and permissions | - | none |

> Team is at **1 to 3% in every nature of business**. It is the least covered function
> in the product.

### Ownership (candidate axis, not the spine)

| Function | Signal | State |
|---|---|---|
| Sending identities (own domain) | `featureUsage.sendingIdentities` | tracked |
| Email template | - | none |
| Document / custom templates | `customtemplates` | measurable, unchecked |
| WhatsApp template | `messagetemplates` | measurable, unchecked |
| Custom fields | `premium.currentCustomFieldsQuota` | measurable, unchecked |
| Remove branding, letterhead | - | none |

## How expected function sets work

**Nature of business gives a prior, not a rule.** Sales already works this way. Nature
sets the pre-sales mindset. The real pitch comes from the conversation.

PLG does the same thing, where behaviour is the conversation:

1. **Start from the prior.** Nature of business sets which functions we expect.
   A trader is expected to need Stock and Books. A knowledge services firm is not.
2. **Update from behaviour.** A knowledge services business that raises a purchase order
   has told us it buys. Buy becomes expected for it, whatever the prior said.
3. **Never subtract on the prior alone.** A prior can add an expectation. Only observed
   behaviour should remove one.

**Businesses with no nature get the General set.** Nature of business was introduced
recently and is blank for about 57% of businesses. The General set is the default
expected set, and it is also the global stage ladder. One mechanism, not two.

## Ranking rule

Rank a function gap by **reach x gap x applicability**. Do **not** rank by conversion
rate.

Rare functions all look spectacular on conversion: credit note 53%, API 56%, bulk upload
36%. Those numbers came from lifetime counters read after conversion, so they mostly
measure what paying customers do once they have paid. Measured properly, in a window
before payment, credit note drops to a 2.1x lift on 3 businesses.

Conversion rate is for **validating** a gap after we pick it. It is not for picking it.

## Still to instrument

Ranked by how much they would change what we can measure:

1. Serial tracking (flag already planned)
2. A warehouse actually created, separate from warehouses being enabled
3. Roles and permissions
4. Email templates, document templates, custom fields
5. RFI / RFQ, vendor forms, package items
6. e-Way bill, TDS / TCS
7. `featureUsage.expenses` correctness
