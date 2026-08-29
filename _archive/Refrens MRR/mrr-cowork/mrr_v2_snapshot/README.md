# MRR v2 Snapshot Workspace

This folder is a fully isolated replacement pipeline for MRR reporting.
It does not modify the original scripts, outputs, or master file in the
parent workspace.

## What changed

- Uses month-end snapshots instead of invoice overlap by month.
- Applies a 2-month inactivity grace window before churn/reactivation.
- Separates `Suspense_MRR` from core SaaS KPIs.
- Excludes forecasting and projection outputs entirely.
- Writes everything inside this folder only.

## Methodology

For each month:

1. Compute the snapshot date as the last day of the month.
2. A subscription is active only if:
   `SubscriptionStart <= snapshot_date < SubscriptionEndExclusive`
3. If multiple invoices overlap for the same `(ClientProfile, Product)`,
   the latest invoice wins for that snapshot date.
4. Sum active product MRR to get client month-end MRR.
5. Build movement metrics from month-end to month-end:
   `NEW`, `REACTIVATION`, `EXPANSION`, `CONTRACTION`, `CHURN`.

## Same-product upgrade heuristic

For true mid-term same-product overlaps inside v2 only:

- if a newer invoice starts after the earlier invoice start but before the earlier end
- and it overlaps the earlier subscription window
- the engine reconstructs a higher effective run-rate by adding back the value of the
  old plan during the overlapped period

This is meant to handle local cases where a customer upgrades mid-term and the invoice
amount is a prorated net charge rather than the full new plan price.

The invoice output exposes both:

- `Invoice_MRR`: raw invoice normalization
- `Effective_Invoice_MRR`: overlap-adjusted run-rate used in month-end MRR

## Grace window

The v2 workspace now applies a 2-month inactivity grace rule for churn:

- first missed month-end is still treated as within grace
- churn is recognized on the second consecutive inactive month-end
- a return after one missed month-end is treated as continuous retention
- a return after two or more missed month-ends is treated as `REACTIVATION`

`SUSPENSE_CLIENT` revenue is reported separately and excluded from:

- `Active_Clients`
- `ARPU`
- `NRR_Pct`
- `GRR_Pct`
- `Logo_Churn_Pct`
- movement buckets

## Files

- `run_mrr_v2.py`: isolated runner
- `audit_churn_v2.py`: independent churn verification against monthly outputs
- `scripts/calculate_mrr_v2.py`: pure-stdlib MRR engine
- `data/master_invoices_v2.csv`: local master copy
- `inbox/`: drop new CSVs here for v2 only
- `output/monthly_summary.csv`: complete month-end history only
- `output/monthly_snapshot.csv`: optional as-of snapshot when `--as-of-date` is supplied
- `output/client_summary.csv`: client-level summary using latest month-end status
- `output/invoices_enriched.csv`: invoice normalization plus month-end movement context

## Commands

Recompute from the local v2 master:

```bash
python3 run_mrr_v2.py --recompute-only
```

Recompute and also emit an as-of snapshot:

```bash
python3 run_mrr_v2.py --recompute-only --as-of-date 2026-03-12
```

Process CSVs dropped into `inbox/` and then recalculate outputs:

```bash
python3 run_mrr_v2.py
python3 audit_churn_v2.py
```

## Notes

- The billing-period mapping remains aligned with the original workspace,
  including `LIFETIME = 84 months`.
- The overlap key is still `(ClientProfile, Product)` because the export
  does not contain a reliable subscription ID.
- `monthly_summary.csv` contains only complete month-end rows.
- `monthly_snapshot.csv` is separate on purpose so incomplete months do not
  contaminate the historical monthly series.
