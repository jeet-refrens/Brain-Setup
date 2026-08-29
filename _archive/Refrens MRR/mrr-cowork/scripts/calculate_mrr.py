#!/usr/bin/env python3
"""
MRR Calculation Script for Refrens Invoice Data
Frozen Methodology v1.0 - January 2026

Usage:
    python calculate_mrr.py <input_csv> [output_directory]

Outputs:
    - monthly_summary.csv
    - client_summary.csv
    - invoices_enriched.csv
"""

import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# =============================================================================
# FROZEN CONFIGURATION
# =============================================================================

PERIOD_MONTHS = {
    'WEEKLY': 0.25,
    'MONTHLY': 1,
    'QUARTERLY': 3,
    'QUATERLY': 3,      # Handle typo in data
    'YEARLY': 12,
    '2YEARLY': 24,
    '3YEARLY': 36,
    '4YEARLY': 48,
    '5YEARLY': 60,
    'LIFETIME': 84      # 7 years amortization
}

SUSPENSE_CLIENT_ID = 'SUSPENSE_CLIENT'

# =============================================================================
# DATA LOADING AND CLEANING
# =============================================================================

def load_and_clean_invoices(filepath):
    """Load invoice CSV and clean data."""
    print(f"Loading data from {filepath}...")
    
    df = pd.read_csv(filepath)
    print(f"  Loaded {len(df)} rows")
    
    # Handle column name variations
    column_mapping = {
        'AmountInINR': 'Amount',
        'InvoiceDate: Day': 'InvoiceDate',
    }
    df = df.rename(columns=column_mapping)
    
    # Clean Amount - remove commas and convert to float
    if 'Amount' in df.columns:
        if not pd.api.types.is_numeric_dtype(df['Amount']):
            df['Amount'] = df['Amount'].astype(str).str.replace(',', '').astype(float)
    else:
        raise ValueError("No Amount column found. Expected 'Amount' or 'AmountInINR'")
    
    # Parse InvoiceDate
    if 'InvoiceDate' in df.columns:
        df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'], format='mixed', errors='coerce')
    else:
        raise ValueError("No InvoiceDate column found")
    
    # Handle missing ClientProfile
    if 'ClientProfile' not in df.columns:
        df['ClientProfile'] = SUSPENSE_CLIENT_ID
    df['ClientProfile'] = df['ClientProfile'].fillna(SUSPENSE_CLIENT_ID)
    df.loc[df['ClientProfile'] == '', 'ClientProfile'] = SUSPENSE_CLIENT_ID
    
    # Calculate period months and MRR
    df['Period'] = df['Period'].str.upper().str.strip()
    df['PeriodMonths'] = df['Period'].map(PERIOD_MONTHS).fillna(12)
    df['MRR'] = df['Amount'] / df['PeriodMonths']
    
    # Derive subscription dates if not present
    if 'SubscriptionStart' not in df.columns:
        df['SubscriptionStart'] = df['InvoiceDate']
        print("  Derived SubscriptionStart from InvoiceDate")
    else:
        df['SubscriptionStart'] = pd.to_datetime(df['SubscriptionStart'], format='mixed', errors='coerce')
    
    if 'SubscriptionEnd' not in df.columns:
        # Calculate end date based on period
        def calc_end_date(row):
            start = row['SubscriptionStart']
            months = row['PeriodMonths']
            if pd.isna(start):
                return pd.NaT
            # Handle fractional months (WEEKLY = 0.25)
            if months < 1:
                days = int(months * 30)
                return start + pd.Timedelta(days=days)
            else:
                return start + relativedelta(months=int(months))
        
        df['SubscriptionEnd'] = df.apply(calc_end_date, axis=1)
        print("  Derived SubscriptionEnd from InvoiceDate + Period")
    else:
        df['SubscriptionEnd'] = pd.to_datetime(df['SubscriptionEnd'], format='mixed', errors='coerce')
    
    # Remove rows with invalid dates
    valid_mask = df['InvoiceDate'].notna() & df['SubscriptionStart'].notna() & df['SubscriptionEnd'].notna()
    invalid_count = (~valid_mask).sum()
    if invalid_count > 0:
        print(f"  Warning: Removing {invalid_count} rows with invalid dates")
    df = df[valid_mask].copy()
    
    print(f"  Cleaned data: {len(df)} invoices")
    return df


# =============================================================================
# MRR CALCULATION WITH OVERLAP HANDLING
# =============================================================================

def build_client_month_mrr(df):
    """
    Build client-month MRR matrix with overlap handling.
    For each (client, product, month), keep only the latest invoice's MRR.
    """
    print("Building client-month MRR (handling overlaps)...")
    
    # Get date range (include subscription coverage, not just invoice dates)
    min_date = min(df['InvoiceDate'].min(), df['SubscriptionStart'].min()).replace(day=1)
    max_date = max(df['InvoiceDate'].max(), df['SubscriptionEnd'].max()).replace(day=1)
    all_months = pd.date_range(start=min_date, end=max_date, freq='MS')
    
    # Cap reporting range at the latest invoice month (future months are for
    # subscription coverage only — projections handle forward-looking estimates)
    latest_invoice_month = df['InvoiceDate'].max().replace(day=1)
    reporting_months = all_months[all_months <= latest_invoice_month]

    print(f"  Date range: {min_date.strftime('%Y-%m')} to {max_date.strftime('%Y-%m')} ({len(all_months)} months)")
    print(f"  Reporting range: {min_date.strftime('%Y-%m')} to {latest_invoice_month.strftime('%Y-%m')} ({len(reporting_months)} months)")

    # Build client-product-month data (handling overlaps)
    client_product_month_data = {}
    
    for idx, row in df.iterrows():
        client = row['ClientProfile']
        product = row['Product']
        mrr = row['MRR']
        start = row['SubscriptionStart'].replace(day=1)
        end = row['SubscriptionEnd'].replace(day=1)
        invoice_date = row['InvoiceDate']
        invoice_id = row['ID']
        
        # Get all months this subscription covers
        covered = all_months[(all_months >= start) & (all_months <= end)]
        
        for month in covered:
            key = (client, product, month)
            if key not in client_product_month_data:
                client_product_month_data[key] = {
                    'mrr': mrr,
                    'invoice_date': invoice_date,
                    'invoice_id': invoice_id
                }
            else:
                # Keep the latest invoice (overlap handling)
                if invoice_date > client_product_month_data[key]['invoice_date']:
                    client_product_month_data[key] = {
                        'mrr': mrr,
                        'invoice_date': invoice_date,
                        'invoice_id': invoice_id
                    }
    
    print(f"  Created {len(client_product_month_data)} client-product-month records")
    
    # Aggregate to client-month level
    client_month_mrr = {}
    for (client, product, month), data in client_product_month_data.items():
        key = (client, month)
        if key not in client_month_mrr:
            client_month_mrr[key] = 0
        client_month_mrr[key] += data['mrr']
    
    # Create pivot table
    records = [(client, month, mrr) for (client, month), mrr in client_month_mrr.items()]
    client_mrr_df = pd.DataFrame(records, columns=['ClientProfile', 'Month', 'MRR'])
    
    pivot = client_mrr_df.pivot_table(
        index='ClientProfile', 
        columns='Month', 
        values='MRR', 
        aggfunc='sum',
        fill_value=0
    )
    
    # Ensure all months present
    for month in all_months:
        if month not in pivot.columns:
            pivot[month] = 0
    pivot = pivot[sorted(pivot.columns)]
    
    print(f"  Created pivot: {len(pivot)} clients × {len(pivot.columns)} months")

    return pivot, all_months, reporting_months


def get_first_month_map(pivot):
    """Get first active month for each client."""
    first_month_map = {}
    for client in pivot.index:
        if client == SUSPENSE_CLIENT_ID:
            continue
        non_zero = pivot.loc[client][pivot.loc[client] > 0]
        if len(non_zero) > 0:
            first_month_map[client] = non_zero.index[0]
    return first_month_map


# =============================================================================
# INVOICE ENRICHMENT
# =============================================================================

def enrich_invoices(df, pivot, first_month_map):
    """Add MRR context and movement type to each invoice."""
    print("Enriching invoice-level data...")
    
    all_months = sorted(pivot.columns)
    invoice_enriched = []
    
    for idx, row in df.iterrows():
        client = row['ClientProfile']
        invoice_month = row['InvoiceDate'].replace(day=1)
        prev_month = invoice_month - relativedelta(months=1)
        invoice_mrr = row['MRR']
        
        # Get client context
        if client in pivot.index and client != SUSPENSE_CLIENT_ID:
            prev_mrr = pivot.loc[client, prev_month] if prev_month in pivot.columns else 0
            curr_mrr = pivot.loc[client, invoice_month] if invoice_month in pivot.columns else 0
            client_first = first_month_map.get(client)
            client_delta = curr_mrr - prev_mrr
        else:
            prev_mrr, curr_mrr, client_delta = 0, 0, 0
            client_first = None
        
        # Classify movement type (invoice-level)
        if client == SUSPENSE_CLIENT_ID:
            movement_type = 'SUSPENSE'
        elif client_first == invoice_month:
            movement_type = 'NEW'
        elif prev_mrr == 0 and curr_mrr > 0:
            movement_type = 'REACTIVATION'
        elif curr_mrr > prev_mrr:
            movement_type = 'EXPANSION'
        elif curr_mrr < prev_mrr:
            movement_type = 'CONTRACTION'
        else:
            movement_type = 'RETAINED_FLAT'
        
        invoice_enriched.append({
            'Invoice_ID': row['ID'],
            'ClientProfile': client,
            'Product_ID': row['Product'],
            'Product_Name': row.get('Product → Name', ''),
            'Period': row['Period'],
            'Invoice_Amount': row['Amount'],
            'Invoice_Date': row['InvoiceDate'].strftime('%Y-%m-%d'),
            'Invoice_Month': invoice_month.strftime('%Y-%m'),
            'Subscription_Start': row['SubscriptionStart'].strftime('%Y-%m-%d'),
            'Subscription_End': row['SubscriptionEnd'].strftime('%Y-%m-%d'),
            'Invoice_MRR': round(invoice_mrr, 2),
            'Client_Prev_Month_MRR': round(prev_mrr, 2),
            'Client_Curr_Month_MRR': round(curr_mrr, 2),
            'Client_MRR_Delta': round(client_delta, 2),
            'Client_First_Month': client_first.strftime('%Y-%m') if client_first else None,
            'Movement_Type': movement_type,
        })
    
    invoice_df = pd.DataFrame(invoice_enriched)
    print(f"  Enriched {len(invoice_df)} invoices")
    return invoice_df


# =============================================================================
# MONTHLY SUMMARY
# =============================================================================

def build_monthly_summary(pivot, first_month_map, invoice_df, reporting_months):
    """Build monthly summary with MRR movements and derived metrics."""
    print("Building monthly summary...")

    all_months_list = sorted(reporting_months)
    monthly_summary = []

    for i, current_month in enumerate(all_months_list):
        prev_month = all_months_list[i - 1] if i > 0 else None
        
        # Initialize counters
        new_mrr, expansion_mrr, reactivation_mrr = 0, 0, 0
        contraction_mrr, churned_mrr = 0, 0
        new_clients, expansion_clients, reactivation_clients = 0, 0, 0
        contraction_clients, churned_clients = 0, 0
        active_clients, total_mrr = 0, 0
        
        # Process each client
        for client in pivot.index:
            if client == SUSPENSE_CLIENT_ID:
                continue
            
            curr_mrr = pivot.loc[client, current_month]
            prev_mrr_val = pivot.loc[client, prev_month] if prev_month is not None else 0
            client_first = first_month_map.get(client)
            
            if curr_mrr > 0:
                active_clients += 1
                total_mrr += curr_mrr
            
            # Classify client movement
            if curr_mrr > 0:
                if client_first == current_month:
                    new_mrr += curr_mrr
                    new_clients += 1
                elif prev_mrr_val == 0:
                    reactivation_mrr += curr_mrr
                    reactivation_clients += 1
                elif curr_mrr > prev_mrr_val:
                    expansion_mrr += (curr_mrr - prev_mrr_val)
                    expansion_clients += 1
                elif curr_mrr < prev_mrr_val:
                    contraction_mrr += (prev_mrr_val - curr_mrr)
                    contraction_clients += 1
            else:
                if prev_mrr_val > 0:
                    churned_mrr += prev_mrr_val
                    churned_clients += 1
        
        # Add SUSPENSE MRR
        suspense_mrr = pivot.loc[SUSPENSE_CLIENT_ID, current_month] if SUSPENSE_CLIENT_ID in pivot.index else 0
        total_mrr += suspense_mrr
        
        # Invoice-level counts
        month_str = current_month.strftime('%Y-%m')
        month_inv = invoice_df[(invoice_df['Invoice_Month'] == month_str) & 
                               (invoice_df['ClientProfile'] != SUSPENSE_CLIENT_ID)]
        
        inv_new_clients = month_inv[month_inv['Movement_Type'] == 'NEW']['ClientProfile'].nunique()
        inv_expansion_clients = month_inv[month_inv['Movement_Type'] == 'EXPANSION']['ClientProfile'].nunique()
        inv_reactivation_clients = month_inv[month_inv['Movement_Type'] == 'REACTIVATION']['ClientProfile'].nunique()
        inv_contraction_clients = month_inv[month_inv['Movement_Type'] == 'CONTRACTION']['ClientProfile'].nunique()
        inv_retained_flat_clients = month_inv[month_inv['Movement_Type'] == 'RETAINED_FLAT']['ClientProfile'].nunique()
        inv_total_clients = month_inv['ClientProfile'].nunique()
        
        # Derived metrics
        net_new_mrr = new_mrr + expansion_mrr + reactivation_mrr - contraction_mrr - churned_mrr
        
        if i > 0:
            beg_mrr = monthly_summary[i-1]['Total_MRR']
            beg_clients = monthly_summary[i-1]['Active_Clients']
        else:
            beg_mrr = 0
            beg_clients = 0
        
        nrr = ((beg_mrr + expansion_mrr - contraction_mrr - churned_mrr) / beg_mrr * 100) if beg_mrr > 0 else None
        grr = ((beg_mrr - contraction_mrr - churned_mrr) / beg_mrr * 100) if beg_mrr > 0 else None
        logo_churn = (churned_clients / beg_clients * 100) if beg_clients > 0 else None
        
        gross_add = new_mrr + expansion_mrr + reactivation_mrr
        gross_loss = contraction_mrr + churned_mrr
        quick_ratio = (gross_add / gross_loss) if gross_loss > 0 else None
        
        arpu = (total_mrr / active_clients) if active_clients > 0 else 0
        
        monthly_summary.append({
            'Month': month_str,
            'Total_MRR': round(total_mrr, 0),
            'Total_ARR': round(total_mrr * 12, 0),
            'Active_Clients': active_clients,
            'Beginning_MRR': round(beg_mrr, 0),
            'New_MRR': round(new_mrr, 0),
            'Expansion_MRR': round(expansion_mrr, 0),
            'Reactivation_MRR': round(reactivation_mrr, 0),
            'Contraction_MRR': round(contraction_mrr, 0),
            'Churned_MRR': round(churned_mrr, 0),
            'Net_New_MRR': round(net_new_mrr, 0),
            'New_Clients': new_clients,
            'Expansion_Clients': expansion_clients,
            'Reactivation_Clients': reactivation_clients,
            'Contraction_Clients': contraction_clients,
            'Churned_Clients': churned_clients,
            'Clients_With_Invoices': inv_total_clients,
            'Inv_New_Clients': inv_new_clients,
            'Inv_Expansion_Clients': inv_expansion_clients,
            'Inv_Reactivation_Clients': inv_reactivation_clients,
            'Inv_Contraction_Clients': inv_contraction_clients,
            'Inv_Retained_Flat_Clients': inv_retained_flat_clients,
            'NRR_Pct': round(nrr, 2) if nrr else None,
            'GRR_Pct': round(grr, 2) if grr else None,
            'Logo_Churn_Pct': round(logo_churn, 2) if logo_churn else None,
            'Quick_Ratio': round(quick_ratio, 2) if quick_ratio else None,
            'ARPU': round(arpu, 0),
        })
    
    monthly_df = pd.DataFrame(monthly_summary)
    print(f"  Created {len(monthly_df)} monthly records")
    return monthly_df


# =============================================================================
# CLIENT SUMMARY (ENRICHED)
# =============================================================================

def build_client_summary(df, pivot, first_month_map, reporting_months):
    """Build enriched client-level summary."""
    print("Building client summary (enriched)...")

    all_months_list = sorted(reporting_months)
    current_month = all_months_list[-1]
    today = pd.Timestamp.now()
    
    # Pre-compute total MRR across all clients for concentration calc (if needed later)
    total_portfolio_mrr = sum(
        pivot.loc[c, current_month] for c in pivot.index if c != SUSPENSE_CLIENT_ID
    )
    
    client_summary = []
    
    for client in pivot.index:
        if client == SUSPENSE_CLIENT_ID:
            continue
        
        client_invoices = df[df['ClientProfile'] == client].sort_values('InvoiceDate')
        
        mrr_history = pivot.loc[client]
        active_months = mrr_history[mrr_history > 0]
        
        if len(active_months) == 0:
            continue
        
        # --- EXISTING FIELDS ---
        first_month = active_months.index[0]
        last_month = active_months.index[-1]
        latest_mrr = active_months.iloc[-1]
        avg_mrr = active_months.mean()
        total_months_active = len(active_months)
        
        total_revenue = client_invoices['Amount'].sum()
        invoice_count = len(client_invoices)
        
        first_invoice = client_invoices['InvoiceDate'].min()
        last_invoice = client_invoices['InvoiceDate'].max()
        
        products = client_invoices['Product → Name'].dropna().unique() if 'Product → Name' in client_invoices.columns else []
        products_str = ', '.join(str(p) for p in products[:5])
        
        current_mrr = pivot.loc[client, current_month]
        is_active = current_mrr > 0
        status = 'ACTIVE' if is_active else 'CHURNED'
        
        # --- NEW: First & Latest subscription period ---
        first_inv = client_invoices.iloc[0]
        latest_inv = client_invoices.iloc[-1]
        first_period = first_inv['Period']
        latest_period = latest_inv['Period']
        
        # --- NEW: First & Latest subscription product ---
        first_product = first_inv.get('Product → Name', first_inv.get('Product', ''))
        latest_product = latest_inv.get('Product → Name', latest_inv.get('Product', ''))
        if pd.isna(first_product) or first_product == '':
            first_product = str(first_inv['Product'])
        if pd.isna(latest_product) or latest_product == '':
            latest_product = str(latest_inv['Product'])
        
        # --- NEW: Renewal count ---
        # A renewal = any invoice after the first one (re-subscriptions)
        renewal_count = max(0, invoice_count - 1)
        
        # --- NEW: MRR trajectory (invoice-to-invoice comparison) ---
        # Compare the last two invoices' normalized MRR
        trajectory = 'NEW'
        if invoice_count >= 2:
            prev_inv = client_invoices.iloc[-2]
            prev_inv_mrr = prev_inv['MRR']
            latest_inv_mrr = latest_inv['MRR']
            
            if latest_inv_mrr > prev_inv_mrr * 1.005:  # >0.5% increase = expanded
                trajectory = 'ACTIVE_EXPANDED'
            elif latest_inv_mrr < prev_inv_mrr * 0.995:  # >0.5% decrease = contracted
                trajectory = 'ACTIVE_CONTRACTED'
            else:
                trajectory = 'ACTIVE_STABLE'
        
        # Override for churned clients
        if not is_active:
            trajectory = 'CHURNED'
        
        # --- NEW: LTV (total revenue collected so far) ---
        ltv = total_revenue
        
        # --- NEW: Expansion revenue ---
        # Sum of (amount - previous amount) for invoices where MRR increased
        expansion_revenue = 0
        for i in range(1, len(client_invoices)):
            curr_inv_mrr = client_invoices.iloc[i]['MRR']
            prev_inv_mrr = client_invoices.iloc[i - 1]['MRR']
            if curr_inv_mrr > prev_inv_mrr:
                # Scale the MRR delta back to the invoice period's amount
                period_months = client_invoices.iloc[i]['PeriodMonths']
                expansion_revenue += (curr_inv_mrr - prev_inv_mrr) * period_months
        
        # --- NEW: Churn & reactivation history ---
        # Walk the monthly MRR history and count gaps (churn events)
        churn_count = 0
        reactivation_count = 0
        prev_mrr_val = 0
        was_ever_active = False
        for mo in all_months_list:
            mo_mrr = mrr_history[mo]
            if mo_mrr > 0 and prev_mrr_val == 0 and was_ever_active:
                reactivation_count += 1
            if mo_mrr == 0 and prev_mrr_val > 0:
                churn_count += 1
            if mo_mrr > 0:
                was_ever_active = True
            prev_mrr_val = mo_mrr
        
        has_reactivated = reactivation_count > 0
        
        # --- NEW: Current plan tier (latest product name) ---
        current_plan = latest_product
        
        # --- NEW: Account age (months from first invoice to now) ---
        account_age_months = (today.year - first_invoice.year) * 12 + (today.month - first_invoice.month)
        
        client_summary.append({
            'ClientProfile': client,
            'Status': status,
            'MRR_Trajectory': trajectory,
            'Current_Plan': current_plan,
            'Current_MRR': round(current_mrr, 2),
            'Latest_MRR': round(latest_mrr, 2),
            'Avg_MRR': round(avg_mrr, 2),
            'ACV': round(latest_mrr * 12, 0),
            
            # Subscription signals
            'First_Period': first_period,
            'Latest_Period': latest_period,
            'First_Product': first_product,
            'Latest_Product': latest_product,
            'Renewal_Count': renewal_count,
            
            # Revenue signals
            'LTV': round(ltv, 0),
            'Expansion_Revenue': round(expansion_revenue, 0),
            'Total_Revenue': round(total_revenue, 0),
            'Invoice_Count': invoice_count,
            
            # Retention signals
            'Has_Reactivated': has_reactivated,
            'Churn_Count': churn_count,
            'Reactivation_Count': reactivation_count,
            
            # Timeline
            'Account_Age_Months': account_age_months,
            'First_Invoice_Date': first_invoice.strftime('%Y-%m-%d'),
            'Last_Invoice_Date': last_invoice.strftime('%Y-%m-%d'),
            'First_Active_Month': first_month.strftime('%Y-%m'),
            'Last_Active_Month': last_month.strftime('%Y-%m'),
            'Months_Active': total_months_active,
            
            'Products': products_str,
        })
    
    client_df = pd.DataFrame(client_summary)
    print(f"  Created {len(client_df)} client records")
    return client_df


# =============================================================================
# VALIDATION
# =============================================================================

def validate_results(monthly_df):
    """Validate calculation results."""
    print("\nValidating results...")
    
    errors = []
    
    for idx, row in monthly_df.iterrows():
        # Check invoice-level counts add up
        sum_inv = (row['Inv_New_Clients'] + row['Inv_Expansion_Clients'] + 
                   row['Inv_Reactivation_Clients'] + row['Inv_Contraction_Clients'] + 
                   row['Inv_Retained_Flat_Clients'])
        
        if sum_inv != row['Clients_With_Invoices']:
            errors.append(f"  {row['Month']}: Invoice counts don't sum ({sum_inv} != {row['Clients_With_Invoices']})")
    
    if errors:
        print("  VALIDATION ERRORS:")
        for err in errors[:5]:
            print(err)
    else:
        print("  ✓ All validations passed")
    
    return len(errors) == 0


# =============================================================================
# MAIN
# =============================================================================

def calculate_mrr(input_filepath, output_dir=None):
    """
    Main function to calculate MRR from invoice data.
    
    Args:
        input_filepath: Path to invoice CSV file
        output_dir: Directory to save output files (default: same as input)
    
    Returns:
        Tuple of (monthly_df, client_df, invoice_df)
    """
    print("=" * 80)
    print("MRR CALCULATION - Refrens Invoice Data")
    print("=" * 80)
    
    # Set output directory
    if output_dir is None:
        output_dir = os.path.dirname(input_filepath) or '.'
    
    # Load and clean data
    df = load_and_clean_invoices(input_filepath)
    
    # Build client-month MRR matrix
    pivot, all_months, reporting_months = build_client_month_mrr(df)
    first_month_map = get_first_month_map(pivot)

    # Generate outputs
    invoice_df = enrich_invoices(df, pivot, first_month_map)
    monthly_df = build_monthly_summary(pivot, first_month_map, invoice_df, reporting_months)
    client_df = build_client_summary(df, pivot, first_month_map, reporting_months)
    
    # Validate
    validate_results(monthly_df)
    
    # Save outputs
    print("\nSaving outputs...")
    
    monthly_path = os.path.join(output_dir, 'monthly_summary.csv')
    client_path = os.path.join(output_dir, 'client_summary.csv')
    invoice_path = os.path.join(output_dir, 'invoices_enriched.csv')
    
    monthly_df.to_csv(monthly_path, index=False)
    client_df.to_csv(client_path, index=False)
    invoice_df.to_csv(invoice_path, index=False)
    
    print(f"  ✓ {monthly_path} ({len(monthly_df)} rows)")
    print(f"  ✓ {client_path} ({len(client_df)} rows)")
    print(f"  ✓ {invoice_path} ({len(invoice_df)} rows)")
    
    # Print summary
    latest = monthly_df.iloc[-1]
    print("\n" + "=" * 80)
    print("SUMMARY (Latest Month: {})".format(latest['Month']))
    print("=" * 80)
    print(f"  Total MRR:      ₹{latest['Total_MRR']:,.0f}")
    print(f"  Total ARR:      ₹{latest['Total_ARR']:,.0f}")
    print(f"  Active Clients: {latest['Active_Clients']}")
    nrr_str = f"{latest['NRR_Pct']:.1f}%" if latest['NRR_Pct'] is not None and not pd.isna(latest['NRR_Pct']) else "N/A"
    qr_str = f"{latest['Quick_Ratio']:.2f}" if latest['Quick_Ratio'] is not None and not pd.isna(latest['Quick_Ratio']) else "N/A"
    print(f"  NRR:            {nrr_str}")
    print(f"  Quick Ratio:    {qr_str}")
    print("=" * 80)
    
    return monthly_df, client_df, invoice_df


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python calculate_mrr.py <input_csv> [output_directory]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    calculate_mrr(input_file, output_dir)
