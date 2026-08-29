#!/usr/bin/env python3
"""
MRR Projection Module
======================

Adds forward-looking projections to monthly_summary.csv:
  - Current partial month → "as-on-date" actuals + "projected" full month
  - Next 2 months → contracted MRR + trend-based overlay

Methodology:
  1. CONTRACTED MRR: For future month M, sum MRR from subscriptions where
     SubscriptionEnd >= M. This is the guaranteed floor.
  2. TREND OVERLAY: 3-month trailing average of New, Expansion, Reactivation,
     Contraction, and Churn MRR. Applied additively on top of contracted base.
  3. PARTIAL MONTH: Current month's invoices received so far are actual. We
     estimate the full month by: contracted MRR for the month (from existing subs)
     + trend-based estimate of new/expansion activity for the remainder.

Usage:
    python project_mrr.py [--as-of-date YYYY-MM-DD] [--months 2]

    --as-of-date    Date up to which invoice data is complete (default: today)
    --months        Number of future months to project beyond current (default: 2)
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
MASTER_FILE = os.path.join(BASE_DIR, 'master_invoices.csv')

PERIOD_MONTHS = {
    'WEEKLY': 0.25, 'MONTHLY': 1, 'QUARTERLY': 3, 'QUATERLY': 3,
    'YEARLY': 12, '2YEARLY': 24, '3YEARLY': 36, '4YEARLY': 48,
    '5YEARLY': 60, 'LIFETIME': 84,
}

SUSPENSE = 'SUSPENSE_CLIENT'
LOOKBACK = 3  # months for trend averaging


def load_data():
    """Load monthly summary and master invoices."""
    monthly_path = os.path.join(OUTPUT_DIR, 'monthly_summary.csv')
    if not os.path.exists(monthly_path):
        raise FileNotFoundError("Run 'python update_mrr.py' first to generate monthly_summary.csv")

    monthly_df = pd.read_csv(monthly_path)

    if not os.path.exists(MASTER_FILE):
        raise FileNotFoundError("No master_invoices.csv found")

    invoices_df = pd.read_csv(MASTER_FILE)
    return monthly_df, invoices_df


def get_contracted_mrr_for_month(invoices_df, target_month_dt):
    """
    Calculate contracted MRR for a target month from raw invoice data.
    Only counts subscriptions that are already paid for and cover the target month.
    Uses the same overlap logic as the main engine (latest invoice wins per client-product-month).
    """
    target_start = target_month_dt.replace(day=1)

    # Normalize columns
    col_map = {'AmountInINR': 'Amount', 'InvoiceDate: Day': 'InvoiceDate'}
    df = invoices_df.rename(columns={k: v for k, v in col_map.items() if k in invoices_df.columns}).copy()

    if not pd.api.types.is_numeric_dtype(df['Amount']):
        df['Amount'] = df['Amount'].astype(str).str.replace(',', '').str.replace('₹', '').str.replace(' ', '').astype(float)

    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'], errors='coerce')
    df['Period'] = df['Period'].str.upper().str.strip()
    df['PeriodMonths'] = df['Period'].map(PERIOD_MONTHS).fillna(12)
    df['MRR'] = df['Amount'] / df['PeriodMonths']

    if 'ClientProfile' not in df.columns:
        df['ClientProfile'] = SUSPENSE
    df['ClientProfile'] = df['ClientProfile'].fillna(SUSPENSE)
    df.loc[df['ClientProfile'] == '', 'ClientProfile'] = SUSPENSE

    if 'SubscriptionStart' not in df.columns:
        df['SubscriptionStart'] = df['InvoiceDate']
    else:
        df['SubscriptionStart'] = pd.to_datetime(df['SubscriptionStart'], errors='coerce')

    if 'SubscriptionEnd' not in df.columns:
        def calc_end(row):
            s = row['SubscriptionStart']
            m = row['PeriodMonths']
            if pd.isna(s): return pd.NaT
            if m < 1: return s + pd.Timedelta(days=int(m * 30))
            return s + relativedelta(months=int(m))
        df['SubscriptionEnd'] = df.apply(calc_end, axis=1)
    else:
        df['SubscriptionEnd'] = pd.to_datetime(df['SubscriptionEnd'], errors='coerce')

    df = df.dropna(subset=['InvoiceDate', 'SubscriptionStart', 'SubscriptionEnd'])

    # Filter: subscription must cover the target month
    df['SubStartMonth'] = df['SubscriptionStart'].apply(lambda d: d.replace(day=1))
    df['SubEndMonth'] = df['SubscriptionEnd'].apply(lambda d: d.replace(day=1))
    covers_target = (df['SubStartMonth'] <= target_start) & (df['SubEndMonth'] >= target_start)
    df_covered = df[covers_target].copy()

    # Overlap handling: latest invoice wins per (client, product)
    df_covered = df_covered.sort_values('InvoiceDate').groupby(
        ['ClientProfile', 'Product']
    ).last().reset_index()

    # Aggregate
    total_mrr = df_covered['MRR'].sum()
    real_clients = df_covered[df_covered['ClientProfile'] != SUSPENSE]['ClientProfile'].nunique()
    suspense_mrr = df_covered[df_covered['ClientProfile'] == SUSPENSE]['MRR'].sum()

    return {
        'total_mrr': total_mrr,
        'active_clients': real_clients,
        'suspense_mrr': suspense_mrr,
        'client_mrr': total_mrr - suspense_mrr,
    }


def compute_trend(monthly_df, n_lookback=LOOKBACK):
    """
    Compute trailing N-month average of MRR movement components.
    Uses the last N COMPLETE months (excludes partial current month if present).
    """
    if len(monthly_df) < 2:
        return {
            'avg_new': 0, 'avg_expansion': 0, 'avg_reactivation': 0,
            'avg_contraction': 0, 'avg_churn': 0, 'avg_net_new': 0,
            'avg_new_clients': 0, 'avg_churn_clients': 0,
        }

    # Use last N rows (these are complete months from the MRR engine)
    window = monthly_df.tail(n_lookback)

    return {
        'avg_new': window['New_MRR'].mean(),
        'avg_expansion': window['Expansion_MRR'].mean(),
        'avg_reactivation': window['Reactivation_MRR'].mean(),
        'avg_contraction': window['Contraction_MRR'].mean(),
        'avg_churn': window['Churned_MRR'].mean(),
        'avg_net_new': window['Net_New_MRR'].mean(),
        'avg_new_clients': window['New_Clients'].mean(),
        'avg_churn_clients': window['Churned_Clients'].mean(),
    }


def build_projections(monthly_df, invoices_df, as_of_date, n_future_months=2):
    """
    Build projection rows for:
      1. Current partial month (actual + projected full month)
      2. N future months (contracted + trend)

    Returns a DataFrame with projection rows to append to monthly_summary.
    """
    print(f"\n{'─' * 70}")
    print(f"  MRR PROJECTIONS (as of {as_of_date.strftime('%Y-%m-%d')})")
    print(f"{'─' * 70}")

    as_of_dt = pd.Timestamp(as_of_date)
    current_month_start = as_of_dt.replace(day=1)
    current_month_str = current_month_start.strftime('%Y-%m')

    # --- Determine which months in monthly_df are "complete" ---
    # A month is complete if it's before the current month
    complete_months = monthly_df[monthly_df['Month'] < current_month_str].copy()

    # Current month actual (may exist in monthly_df if invoices were dated this month)
    current_actual = monthly_df[monthly_df['Month'] == current_month_str]

    print(f"  Complete historical months: {len(complete_months)}")
    print(f"  Current month ({current_month_str}): {'has actual data' if len(current_actual) else 'no invoices yet'}")

    # --- Trend from last 3 complete months ---
    trend = compute_trend(complete_months, LOOKBACK)
    lookback_used = min(LOOKBACK, len(complete_months))
    print(f"  Trend lookback: {lookback_used} months")
    print(f"    Avg New MRR:        ₹{trend['avg_new']:,.0f}")
    print(f"    Avg Expansion MRR:  ₹{trend['avg_expansion']:,.0f}")
    print(f"    Avg Reactivation:   ₹{trend['avg_reactivation']:,.0f}")
    print(f"    Avg Contraction:    ₹{trend['avg_contraction']:,.0f}")
    print(f"    Avg Churn MRR:      ₹{trend['avg_churn']:,.0f}")
    print(f"    Avg Net New:        ₹{trend['avg_net_new']:,.0f}")

    projection_rows = []

    # --- CURRENT MONTH: Actual (as-on-date) ---
    if len(current_actual):
        actual_row = current_actual.iloc[0].to_dict()
        actual_row['Month'] = f"{current_month_str} (actual as of {as_of_date.strftime('%b %d')})"
        actual_row['Row_Type'] = 'ACTUAL_PARTIAL'
        projection_rows.append(actual_row)

    # --- CURRENT MONTH: Projected full month ---
    # Contracted MRR = what existing subs guarantee for this full month
    contracted = get_contracted_mrr_for_month(invoices_df, current_month_start)

    # For the partial month, we know some new/expansion already happened (in actual).
    # Estimate remaining: scale the trend proportionally by remaining days.
    import calendar
    days_in_month = calendar.monthrange(as_of_date.year, as_of_date.month)[1]
    days_elapsed = as_of_date.day
    days_remaining = days_in_month - days_elapsed
    remaining_fraction = days_remaining / days_in_month

    # Already-captured new/expansion from actual invoices this month
    actual_new = current_actual.iloc[0]['New_MRR'] if len(current_actual) else 0
    actual_exp = current_actual.iloc[0]['Expansion_MRR'] if len(current_actual) else 0
    actual_react = current_actual.iloc[0]['Reactivation_MRR'] if len(current_actual) else 0

    # Projected additional from remaining days (trend × remaining fraction)
    proj_add_new = trend['avg_new'] * remaining_fraction
    proj_add_exp = trend['avg_expansion'] * remaining_fraction
    proj_add_react = trend['avg_reactivation'] * remaining_fraction

    # Contracted base already includes existing subs; add trend-based new activity
    proj_current_mrr = contracted['total_mrr'] + actual_new + proj_add_new + actual_exp + proj_add_exp + actual_react + proj_add_react

    # Churn/contraction for the month: use full month trend (these happen throughout the month)
    proj_contraction = trend['avg_contraction']
    proj_churn = trend['avg_churn']

    # But contracted MRR already reflects subs that ended — so churn is already baked in
    # We only need to add trend-based churn for clients whose subs end this month but
    # we can't predict which ones. Simplification: use contracted as base, add net new activity.
    proj_current_total = contracted['total_mrr'] + (actual_new + proj_add_new) + (actual_exp + proj_add_exp) + (actual_react + proj_add_react)
    proj_current_clients = contracted['active_clients'] + round(trend['avg_new_clients'] * remaining_fraction)

    projection_rows.append({
        'Month': f"{current_month_str} (projected)",
        'Row_Type': 'PROJECTED',
        'Total_MRR': round(proj_current_total, 0),
        'Total_ARR': round(proj_current_total * 12, 0),
        'Active_Clients': proj_current_clients,
        'Beginning_MRR': complete_months.iloc[-1]['Total_MRR'] if len(complete_months) else 0,
        'Contracted_MRR': round(contracted['total_mrr'], 0),
        'Trend_New_MRR': round(actual_new + proj_add_new, 0),
        'Trend_Expansion_MRR': round(actual_exp + proj_add_exp, 0),
        'Trend_Reactivation_MRR': round(actual_react + proj_add_react, 0),
        'Trend_Contraction_MRR': round(proj_contraction, 0),
        'Trend_Churn_MRR': round(proj_churn, 0),
        'NRR_Pct': None,
        'GRR_Pct': None,
        'Logo_Churn_Pct': None,
        'Quick_Ratio': None,
        'ARPU': round(proj_current_total / proj_current_clients, 0) if proj_current_clients > 0 else 0,
    })

    # --- FUTURE MONTHS ---
    prev_projected_mrr = proj_current_total

    for offset in range(1, n_future_months + 1):
        future_dt = current_month_start + relativedelta(months=offset)
        future_str = future_dt.strftime('%Y-%m')

        # Contracted base for this future month
        contracted_f = get_contracted_mrr_for_month(invoices_df, future_dt)

        # Trend overlay: full month of avg new/expansion/reactivation
        proj_new = trend['avg_new']
        proj_exp = trend['avg_expansion']
        proj_react = trend['avg_reactivation']
        proj_contr = trend['avg_contraction']
        proj_ch = trend['avg_churn']

        # Projected MRR = contracted + full trend additions
        proj_mrr = contracted_f['total_mrr'] + proj_new + proj_exp + proj_react
        proj_clients = contracted_f['active_clients'] + round(trend['avg_new_clients']) - round(trend['avg_churn_clients'])

        projection_rows.append({
            'Month': f"{future_str} (projected)",
            'Row_Type': 'PROJECTED',
            'Total_MRR': round(proj_mrr, 0),
            'Total_ARR': round(proj_mrr * 12, 0),
            'Active_Clients': max(0, proj_clients),
            'Beginning_MRR': round(prev_projected_mrr, 0),
            'Contracted_MRR': round(contracted_f['total_mrr'], 0),
            'Trend_New_MRR': round(proj_new, 0),
            'Trend_Expansion_MRR': round(proj_exp, 0),
            'Trend_Reactivation_MRR': round(proj_react, 0),
            'Trend_Contraction_MRR': round(proj_contr, 0),
            'Trend_Churn_MRR': round(proj_ch, 0),
            'NRR_Pct': None,
            'GRR_Pct': None,
            'Logo_Churn_Pct': None,
            'Quick_Ratio': None,
            'ARPU': round(proj_mrr / max(1, proj_clients), 0),
        })

        prev_projected_mrr = proj_mrr

    proj_df = pd.DataFrame(projection_rows)
    return proj_df


def run_projections(as_of_date=None, n_months=2):
    """Main entry point."""
    if as_of_date is None:
        as_of_date = date.today()
    elif isinstance(as_of_date, str):
        as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()

    monthly_df, invoices_df = load_data()
    proj_df = build_projections(monthly_df, invoices_df, as_of_date, n_months)

    # Print projection summary
    print(f"\n  {'─' * 60}")
    print(f"  {'PROJECTION SUMMARY':^60}")
    print(f"  {'─' * 60}")
    print(f"  {'Month':<32} {'MRR':>12} {'Contracted':>12} {'Clients':>8}")
    print(f"  {'─' * 60}")

    for _, row in proj_df.iterrows():
        contracted = row.get('Contracted_MRR', '')
        contracted_str = f"₹{contracted:,.0f}" if pd.notna(contracted) and contracted != '' else '—'
        mrr_str = f"₹{row['Total_MRR']:,.0f}"
        clients_str = str(int(row['Active_Clients'])) if pd.notna(row['Active_Clients']) else '—'
        row_type = row.get('Row_Type', '')

        if row_type == 'ACTUAL_PARTIAL':
            marker = '  📍'
        else:
            marker = '  🔮'

        print(f"{marker} {row['Month']:<30} {mrr_str:>12} {contracted_str:>12} {clients_str:>8}")

    print(f"  {'─' * 60}")

    # Save
    proj_path = os.path.join(OUTPUT_DIR, 'projections.csv')
    proj_df.to_csv(proj_path, index=False)
    print(f"\n  💾 Saved: {proj_path} ({len(proj_df)} rows)")

    # Also save a combined view (historical + projections)
    combined_path = os.path.join(OUTPUT_DIR, 'monthly_with_projections.csv')
    # Add Row_Type to historical rows
    monthly_df['Row_Type'] = 'ACTUAL'
    combined = pd.concat([monthly_df, proj_df], ignore_index=True)
    combined.to_csv(combined_path, index=False)
    print(f"  💾 Saved: {combined_path} ({len(combined)} rows)")

    return proj_df


if __name__ == '__main__':
    as_of = None
    n_months = 2

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--as-of-date' and i + 1 < len(args):
            as_of = args[i + 1]
            i += 2
        elif args[i] == '--months' and i + 1 < len(args):
            n_months = int(args[i + 1])
            i += 2
        else:
            i += 1

    run_projections(as_of_date=as_of, n_months=n_months)
