# Accounting — Schema

## Summary

> Curated from live `saturn` migrations, `talos` models and `fence` enums, verified **2026-08-15**.
> Field-for-field truth is in **Source of truth** below — use it (via the GitHub API) whenever
> exact types/enums matter.
>
> **Two datastores.** Saturn = PostgreSQL (snake_case columns, UUID PKs). Talos = MongoDB
> (camelCase, ObjectId). They are joined by **string IDs stored as plain strings**, not real
> foreign keys — Saturn stores `business` as a Mongo business id string; Mongo stores `ledgerId`
> as a Saturn UUID string.

### Saturn (PostgreSQL) — the books

| Table | Key columns (curated) | Notes |
|---|---|---|
| **`accountgroups`** | `id`(uuid), `name`, `default_key`, `business`, `account_group_type`(enum), `account_type`(enum), `document_type`(enum), `is_hard_removed`, `hard_removed_at`, `meta`(json), `created_by`/`updated_by` | Chart-of-accounts groups. Unique on `(business, name, account_type, account_group_type)`. `default_key` set only for system-generated groups. |
| **`ledgers`** | `id`, `business`, `name`, `default_key`, `account_group`→`accountgroups`(CASCADE), `account_group_type`, `account_type`, `document_type`, `document_refers_to`(enum), `document_reference_id`, `notes`, `is_archived`, `is_hard_removed`, `meta` | Individual accounts. `document_refers_to` + `document_reference_id` is the **bridge to Mongo** (client / vendor / employee / SKU / bank account). Unique on `(business, name, account_group)`. |
| **`vouchers`** | `id`, `business`, `name`, `default_key`, `voucher_type`(enum), `document_type`, `document_refer_to`(enum), `notes`, `is_archived`, `is_hard_removed`, `meta` | Voucher **books**, not entries. Unique on `(business, name, voucher_type)`. |
| **`voucher_entries`** | `id`, `voucher_number`(int), `voucher_id`→`vouchers`, `voucher_type`, `financial_year`→`financial_years`, `business`, `debits`(json), `credits`(json), `total`, `currency`, `book_total`, `book_currency`, `currency_wise_total`(json), `voucher_date`, `narration`, `document_type`, `document_refers_to`(billType), `refrens_document_no`, `document_reference_id`, `original_voucher_entry`(uuid), `version`(int), `reversed`, `reversal_entry`, `is_hard_removed`, `meta` | The posted entry. `document_reference_id` / `refrens_document_no` point back at the Mongo document. Numbering is assigned by a DB trigger (see migration `20251013000000_voucher_numbering_trigger`). |
| **`lineitems`** | `id`, `crdr`(`cr`/`dr`), `ledger`→`ledgers`, `voucher_entry`→`voucher_entries`, `voucher_id`, `financial_year_id`, `business`, `remark`, `amount`(int), `currency`, `book_amount`(int), `book_currency`, `forex_rate`(float), `voucher_date`, `voucher_number`, `is_reversed`, `is_reversal_entry`, `is_hard_removed`, `meta` | One row per Dr/Cr leg. This is the table reports aggregate over. |
| **`financial_years`** | `id`, `business`, `label`, `start_date`, `end_date`, `is_hard_removed`, `meta` | Unique on `(business, label)`. FY start month varies by country — see `fence/accounting/fyByCountry.json`. |
| **`fy_wise_ledgers_data`** | per-`(business, financial_year, ledger)` opening/closing balance rollup | Makes balance reads cheap instead of summing all line items. |
| **`fy_wise_vouchers_data`** | per-`(business, financial_year, voucher)` numbering/rollup state | Drives voucher numbering per FY. |

**Bank reconciliation tables:**

| Table | Key columns (curated) |
|---|---|
| **`bank_statements`** | `id`, `business`, `payment_account`, `ledger`(uuid), `account_info`(jsonb), `file_name`, `file_url`, `source`(enum), `source_format`(enum), `status`, `opening_balance`/`opening_balance_type`, `closing_balance`/`closing_balance_type`, `total_credit`, `total_debit`, `credit_count`, `debit_count`, `total_transactions`, `currency`, `start_date`, `end_date`, `all_transactions_in_bankbook` |
| **`bank_transactions`** | `id`, `business`, `transaction_date`, `remarks`, `reference_number`, `type`, `amount`, `closing_balance`/`closing_balance_type`, `currency`, `order`, `is_duplicate`, `is_ignored`, `bank_book_created`, `payment_account` — *what the bank statement says* |
| **`bank_books`** | same shape as `bank_transactions` plus `payment_account` — *what the books say* |
| **`reconciliations`** | `id`, `business`, `status`(enum), `type`, `action_type`(`MANUAL`/`AUTO`), `date`, `total`, `currency`, `notes` |
| **`reconciliation_bank_books`** | `id`, `reconciliation`→`reconciliations`(CASCADE), `bank_book`→`bank_books`(CASCADE), `business`, `is_hard_removed`/`hard_removed_at`/`hard_removed_by`, `meta` — join table |
| **`reconciliation_lineitems`** | `id`, `reconciliation`→`reconciliations`, `lineitem`→`lineitems`, `business`, same soft-remove columns — join table tying a reconciliation to the ledger legs it matched |

### Talos (MongoDB) — the feeders

| Collection | Key fields (curated) | Notes |
|---|---|---|
| **`paymentrecords`** | `paymentReceiptTitle`/`Number`/`Date`, `billType`(`PAYMENTRECORD`/`PAYOUTRECORD`), `status`(default `SETTLED`), `isAdvance`, `isRefund`, `isPettyPayout`, `settledInvoices[]{invoice→invoices, payment, transaction→transactions, amount, tds, transactionCharge, conversionRates}`, `totals{tds, transactionCharge, amount, settledAmount, advance, total, totalRoundOff, amountRoundOff}`, `totalConversions` | Shares the `documentCommonFields` helpers with `invoices`. One record can settle many invoices. |
| **`transactions`** | `currency`(req), `amount`(req), `debit`→`wallets`(req), `credit`→`wallets`(req), `type`(enum), `status`(default `PENDING`), `narration`, `conversionRates`, `bookedAt`, `settledAt`, `paymentLedgerId`, `paymentLedgerName`, `paymentVoucherEntryRefrence`, `forexVoucherEntryRefrence`, `bookKeepingSyncStatus{isSynced, errorMessage, syncSource}`, `lead`→`leads`, `params` | Wallet-to-wallet money movement — **not** the double-entry books. `paymentLedgerId` / `paymentVoucherEntryRefrence` are the links into Saturn. Note the two misspelled fields (`Refrence`). |
| **`wallets`** | `isRefrens`, `isBusiness`, `refType`, `balance`(Map currency→Number), `pendingBalance`(Map), `lastUpdate`, `lastSettlement`, `lastUserPayout` | Multi-currency balances held as Maps. |
| **`paymentAccounts`** | `ledgerId`(**Saturn ledger UUID**), `business`, `name`(req), `accountType`(default `OTHER`), `linkedBank`→`bankaccounts`, `linkedEmployee`→`employeeaccounts`, `vpa`(UPI), `customFields[]`, `vendorFields`, `isRemoved`/`isHardRemoved` | The user-facing "paid into / paid from" account. The single most important Mongo↔Saturn mapping for payments. |
| **`bankAccounts`** | `business`, `accountNo`, `ifsc`, `iban`, `sortCode`, `swift`, `name`, `accountType`, `bank`, `phone`, `country`, `currency`, `isVerified`, `penny`, `attempts`, `validationError`, `isPrimary`, `customLabels`, `customFields`, `vendorFields` | Covers both Indian (IFSC) and international (IBAN/SWIFT/sort code) formats. |
| **`gstReturns`** | `business`, `source`, `format`, `type`, `filePath`, `data`, `checksum`, `filingDate`, `uploadedDate`, `period`, `referenceRequest`, `xlsx` | Filed/uploaded return artifacts. |
| **`gstFilings`** | `gstin`, `name`, `alias`, `status`, `registrationDate`, `taxPayerType`, `ctb`, `einvoiceStatus`, address block (`address`, `city`, `pincode`, `gstState`, `adadr`), `natureOfBusiness`, `filings[]{rtntype, ret_prd, periodLabel, dof, filingDate, dueDate, arn, status, isLate, delayDays, isOptional, isMissed}`, `complianceSummary{missedCount, score, totalExpected, totalFiled, onTime, late, missed, lastFiledMonth}`, `filingPreference`, `lastSyncedAt`, `isRefrensBusiness` | Filing-history + compliance-score tracking per GSTIN. |
| **`gstr2bEntries`** | `business`, `reportId`, `businessGstin`, `vendorGstin`, `vendorName`, `vendor`, `invoiceNumber`, `invoiceDate`, `period`, `irn`, `pos`, `rev`, `itcavl`, `itcelg`, `rsn`, `diffprcnt`, `totals`, `items`, `suptyp`, `doctyp`, `reconciliation`, `linkedDocument`, `category` | Inbound GSTR-2B lines for ITC reconciliation against purchases. |
| **`businessConfigurations.syncAccounting`** | `accountingSetup`, `invoice`, `creditNote`, `debitNote`, `expenditure`, `invoicePayment`, `expenditurePayment`, `debitNotePayment`, `paymentReceipt`, `client`, `paymentAccounts` — each a `SyncDocument`; plus `allowBackDateEntries`, `allowVoucherEntryEdit` | `SyncDocument` = `{status: NONE\|REQUESTED\|SCHEDULED\|DONE\|FAILED, voucherId, creditLedgerId, debitLedgerId, totalDocumentToSync, totalDocumentSynced, revalidated}`. **This is the master gate for whether accounting exists at all for a business.** |

### Enums (exact, from `fence/accounting`)

- **`accountType`**: `asset` · `liability` · `income` · `expense` · `capital`.
- **`accountGroupType`** (45 keys): `FDR`, `bankAccounts`, `cashInHand`, `loansAndAdvances`,
  `sundryDebtors`, `TDS`, `deposits`, `stockInHand`, `security`, `machinery`, `land`, `vehicle`,
  `bankODAc`, `branchDivisions`, `capitalAccount`, `currentLiabilities`, `dutiesAndTaxes`, `loans`,
  `provisions`, `reservesAndSurplus`, `securedLoans`, `sundryCreditors`, `suspense`,
  `unsecuredLoans`, `legalHRExpenses`, `administrativeExpenses`, `depreciationExpenses`,
  `directExpenses`, `employeesCost`, `financialExpenses`, `indirectExpenses`, `miscExpenses`,
  `promotionalExpenses`, `purchaseAccounts`, `directIncomes`, `indirectIncomes`, `salesAccounts`,
  `purchaseReturn`, `salesReturn`, `currentAssets`, `fixedAssets`, `equities`, `building`,
  `costOfGoodsSold`, `inputTDS`, `inputDutiesAndTaxes`.
- **`voucherType`**: `contra`, `journal`, `reversingJournal`, `payment`, `receipt`, `debitNote`,
  `creditNote`, `receiptNote`, `memorandum`, `salesOrder`, `deliveryNote`, `sales`, `purchase`,
  `purchaseOrder`, `rejectionsIn`, `rejectionsOut`, `stockJournal`, `physicalStock`, `reimbursement`.
- **`documentType`** (provenance of the record): `systemGenerated` · `userGenerated` · `seranaSync`.
- **`creditDebitType`**: `cr` · `dr`.
- **`documentRefersToLedgerType`**: `client` · `vendor` · `clientVendor` · `vendorClient` ·
  `employee` · `sku` · `bankAccount`.
- **`documentRefersToVoucherType`**: `invoice` · `expenditure` · `debitNote` · `creditNote` ·
  `payment` · `reciept` *(sic — misspelled in `fence`)*.
- **`syncSource`**: `COMMAND` · `DOCUMENT` · `BUSINESS` · `RESYNC` · `ENTRY_CHANGE`.
- **`syncBreakReasons`**: `REVERSAL_VOUCHER_ENTRY_CREATED`,
  `REVERSAL_PAYMENT_VOUCHER_ENTRY_CREATED`, `DOCUMENT_CANCELED`, `DOCUMENT_SOFT_DELETED`,
  `DOCUMENT_HARD_DELETED`.
- **`bankStatementSource`**: `MANUAL_UPLOAD` · `API_IMPORT` · `BANK_FEED`.
  **`bankStatementFormat`**: `PDF` · `EXCEL` · `CSV`.
- **`bankStatementStatus`**: `UPLOADED`, `REVIEW_PENDING`, `PROCESSING`, `FAILED`,
  `ADDED_TO_BANK_BOOK`, `REJECTED`, `ADDING_ALL_BANK_BOOK`, `RECONCILIATION_IN_PROGRESS`,
  `RECONCILIATION_COMPLETED`, `ADDING_ALL_BANK_BOOK_FAILED`, `RECONCILIATION_FAILED`.
- **`reconciliationStatus`**: `MATCHED`, `MISSING_IN_LEDGER`, `MISSING_IN_BANK_BOOK`, `DISCARDED`,
  `MARKED_FOR_LATER`, `RECONCILED`. **`reconciliationActionType`**: `MANUAL` · `AUTO`.
- **`voucher_entries.document_refers_to`** uses `fence/invoices/billType.json` **plus** an extra
  `'EXPENDITURE'` value appended in `saturn/src/helpers/enums.ts` — it is *not* purely the fence enum.

### Default chart of accounts

System ledgers are created from `fence/accounting/ledgerDefaultKeys.json` (~75 entries), each with a
stable `key` and its parent `accountGroupKey`. Groups come from
`fence/accounting/defaultAccountGroupTemplate.json`; vouchers from
`fence/accounting/defaultVoucherData.json`. Keys are namespaced:

- `REF_DEFAULT_*` — current system ledgers, e.g. `REF_DEFAULT_Cash`, `REF_DEFAULT_Round_Off`,
  `REF_DEFAULT_Item_Discount`, `REF_DEFAULT_Total_Discount`, `REF_DEFAULT_Extra_Charges`,
  `REF_DEFAULT_Forex`, `REF_DEFAULT_Stock_In_Hand`, `REF_DEFAULT_Cost_Of_Goods_Sold`,
  `REF_DEFAULT_Retained_Earnings`, `REF_DEFAULT_Current_Year_Earnings`, `REF_DEFAULT_Closing_Stock`.
- `REF_Legacy_*_Payment_Mode` — legacy per-payment-mode ledgers (Account Transfer, UPI, Cheque, DD,
  Credit/Debit Card, Digital Wallet, Prepaid Card, Refrens, Proforma, Other). Superseded by
  `paymentAccounts` but still present on older businesses.
- **Tax ledgers are country-aware**, gated by `includedCurrencies`/`excludedCurrencies` on each
  entry: GST (`Sales_IGST/CGST/SGST/UTGST`, `Purchase_*`, `*_Input`, `*_Reverse_Charge`, `Cess`)
  for India, and `Sales_VAT`, `Sales_SST`, `Sales_PPN`, `Sales_HST`, `Sales_TAX` plus their
  purchase/reverse-charge counterparts elsewhere. **Don't assume GST-only ledgers exist.**

### Relationships

```
accountgroups 1─N ledgers 1─N lineitems N─1 voucher_entries N─1 vouchers
                                    │                  │
                          financial_years ─────────────┘

clients.ledgerId ──────────────┐
paymentAccounts.ledgerId ──────┼──► saturn ledgers.id     (Mongo string ↔ PG uuid)
                               │
invoices._id ──────────────────┴──► voucher_entries.document_reference_id
transactions.paymentVoucherEntryRefrence ──► voucher_entries.id
```

- `voucher_entries.original_voucher_entry` + `version` form the correction chain;
  `reversed`/`reversal_entry` mark a reversed entry.
- `clients.previousLedgers[]` keeps historical ledger ids after a client's ledger is re-pointed.
- Inventory items carry `salesLedger`/`purchaseLedger`/`inventoryLedger` — see
  [../inventory/schema.md](../inventory/schema.md).

## Source of truth

`gh` was not installed at last verification; contents were read via the GitHub REST API
(reference `GITHUB_PAT` **by name only**). Or run `/sync-schema accounting`.

- **`refrens/saturn`** — `migrations/20230206002317_accountgroup.ts`, `20230206060329_voucher.ts`,
  `20230206124919_ledger.ts`, `20230208141433_financial_years.ts`, `20230213131142_voucher_entries.ts`,
  `20230213134349_lineitems.ts`, `20230216001415_fy-wise-ledgers.ts`,
  `20250521060343_bank-statements.ts` → `20250620075603_reconciliation-lineitems.ts`;
  `src/helpers/enums.ts`, `src/helpers/ensure-system-accounts.ts`,
  `src/helpers/compute-ledger-balance.ts`; `src/services/*` (accountgroup, ledger, voucher,
  voucher-entries, lineitems, financial-years, reports, sync-accounting, sync-payments,
  reverse-entries, bank-*, reconciliation*).
- **`refrens/fence`** — `accounting/accountGroupType.json`, `accountType.json`, `documentType.json`,
  `voucherType.json`, `creditDebitType.json`, `documentRefersToLedgerType.json`,
  `documentRefersToVoucherType.json`, `ledgerDefaultKeys.json`, `defaultAccountGroupTemplate.json`,
  `defaultVoucherData.json`, `fyByCountry.json`, `syncSource.json`, `syncBreakReasons.json`,
  `bankStatement*.json`, `reconciliation*.json`, `voucher-entry-ledger-filters.json`.
- **`refrens/talos`** — `src/paymentrecords.js`, `transactions.js`, `wallets.js`,
  `paymentAccounts.js`, `bankAccounts.js`, `paymentlinks.js`, `gstReturns.js`, `gstFilings.ts`,
  `gstr2bEntries.js`, `gstrVendors.js`, `businessConfigurations.ts` (`syncAccounting` block,
  ~line 414).
- **`refrens/serana`** — `src/hooks/sync-document-with-voucher-entries.js` (the posting trigger),
  `src/helpers/shouldSyncDocument.js`, `src/helpers/documentConfig.js`, and services
  `sync-accounting`, `sync-payments`, `invoice-voucher-entries`, `voucher-entry-batch`,
  `ledger-batch`, `ledger-statement`, `client-ledger`, `gst-*`.
- **Fetch pattern** (no `gh`; PAT referenced by name, never printed):
  ```bash
  curl -s -H "Authorization: Bearer $GITHUB_PAT" -H "Accept: application/vnd.github.raw" \
    "https://api.github.com/repos/refrens/saturn/contents/src/helpers/enums.ts"
  ```
