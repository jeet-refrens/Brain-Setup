# MRR Tracker — Cowork Folder Instructions

This folder tracks Monthly Recurring Revenue (MRR) for Refrens from invoice data.

## Quick Commands

When Vaidik says **"Update MRR"** or **"Run MRR"**:
1. Run `python update_mrr.py` from this folder
2. The script will: pick up CSVs from `inbox/`, deduplicate against `master_invoices.csv`, append new invoices, run the full MRR calculation, and generate projections
3. After the script finishes, summarize the latest month's key metrics from `output/monthly_summary.csv`: Total MRR, ARR, Active Clients, NRR%, and Net New MRR breakdown. Also share the projection summary from `output/projections.csv`.

When Vaidik says **"Update MRR as of [date]"** (e.g. partial month):
1. Run `python update_mrr.py --as-of-date YYYY-MM-DD`
2. This tells the projection engine how many days of the current month have data, so it can estimate the remaining activity

When Vaidik says **"Recompute MRR"** (no new data, just rerun):
1. Run `python update_mrr.py --recompute-only`

When Vaidik says **"Project MRR"** (just projections, no merge):
1. Run `python project_mrr.py --as-of-date YYYY-MM-DD`

When Vaidik asks about **specific clients, churn, or trends**:
1. Read the relevant CSV from `output/` and analyze

## Folder Structure

```
mrr-cowork/
├── INSTRUCTIONS.md          ← You're reading this (Cowork folder instructions)
├── update_mrr.py            ← Main pipeline script (merge + calculate + project)
├── project_mrr.py           ← Standalone projection script
├── master_invoices.csv      ← Full historical invoice dataset (auto-maintained)
├── scripts/
│   └── calculate_mrr.py     ← Frozen MRR methodology v1.1 (patched)
├── inbox/                   ← Drop new invoice CSVs here
│   └── processed/           ← Processed files are archived here
└── output/                  ← MRR calculation results
    ├── monthly_summary.csv          ← One row per month: MRR, movements, NRR, GRR
    ├── client_summary.csv           ← One row per client: status, revenue, products
    ├── invoices_enriched.csv        ← Each invoice tagged with movement type
    ├── projections.csv              ← Current partial month + 2-month forward projections
    └── monthly_with_projections.csv ← Historical + projections combined view
```

## Workflow

1. Export invoices from Refrens (Premium/subscription invoices only)
2. Drop the CSV into `inbox/`
3. Say "Update MRR"
4. Results appear in `output/`

The master file grows over time. Inbox files are archived after processing. Deduplication is by Invoice `ID` column — uploading the same file twice won't create duplicates.

## Expected CSV Format

Required columns: `ID`, `ClientProfile`, `Product`, `Amount` (or `AmountInINR`), `InvoiceDate` (or `InvoiceDate: Day`), `Period`

Optional columns: `Product → Name`, `SubscriptionStart`, `SubscriptionEnd` (derived from InvoiceDate + Period if missing)

Period values: WEEKLY, MONTHLY, QUARTERLY, YEARLY, 2YEARLY, 3YEARLY, 4YEARLY, 5YEARLY, LIFETIME

## Methodology

Frozen MRR methodology v1.1. See `scripts/calculate_mrr.py` header for full documentation. Key rules:
- MRR = Amount / PeriodMonths
- Overlapping subscriptions: latest invoice wins (prevents double-counting)
- Movements: NEW → EXPANSION → REACTIVATION → CONTRACTION → CHURN
- SUSPENSE_CLIENT: invoices without ClientProfile (counted in MRR totals, excluded from client metrics)
- LIFETIME amortized over 7 years (84 months)

## Projection Methodology

The projection engine (`project_mrr.py`) generates forward estimates:

1. **Contracted MRR** (floor): For each future month, sum MRR from subscriptions whose `SubscriptionEnd` >= that month. This is revenue already paid for — guaranteed.

2. **Trend overlay**: 3-month trailing average of New, Expansion, Reactivation MRR added on top of contracted base. Represents expected sales activity based on recent performance.

3. **Partial month handling**: For the current month (e.g. Feb 18 of 28 days):
   - "Actual" row: exactly what invoices show as of today
   - "Projected" row: Contracted MRR + actual new/expansion so far + remaining-days-fraction × trend rates

4. **Output rows** are tagged with `Row_Type`:
   - `ACTUAL` = historical complete months
   - `ACTUAL_PARTIAL` = current month as-on-date
   - `PROJECTED` = estimated future months
