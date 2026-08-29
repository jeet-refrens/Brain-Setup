#!/usr/bin/env python3
"""
MRR Update Pipeline for Cowork
================================

Drop a new invoice CSV into the /inbox folder, then tell Cowork:
  "Update MRR"

This script will:
  1. Pick up any CSV files in /inbox
  2. Deduplicate against master_invoices.csv by Invoice ID
  3. Append new invoices to master_invoices.csv
  4. Run the full MRR calculation
  5. Move processed inbox files to /inbox/processed
  6. Output results to /output

Usage:
    python update_mrr.py [--recompute-only]
    
    --recompute-only    Skip inbox merge, just recompute from master_invoices.csv
"""

import pandas as pd
import os
import sys
import glob
import shutil
from datetime import datetime

# =============================================================================
# PATHS (relative to this script's directory)
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_FILE = os.path.join(BASE_DIR, 'master_invoices.csv')
INBOX_DIR = os.path.join(BASE_DIR, 'inbox')
PROCESSED_DIR = os.path.join(BASE_DIR, 'inbox', 'processed')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
SCRIPT_DIR = os.path.join(BASE_DIR, 'scripts')

# Ensure directories exist
for d in [INBOX_DIR, PROCESSED_DIR, OUTPUT_DIR, SCRIPT_DIR]:
    os.makedirs(d, exist_ok=True)


# =============================================================================
# COLUMN NORMALIZATION
# =============================================================================

def normalize_columns(df):
    """
    Normalize column names so any Refrens export variant works.
    Returns a DataFrame with canonical column names.
    """
    rename_map = {
        'AmountInINR': 'Amount',
        'InvoiceDate: Day': 'InvoiceDate',
        'ProductName': 'Product → Name',
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    
    # Clean Amount: handle commas, currency symbols, spaces
    if 'Amount' in df.columns and not pd.api.types.is_numeric_dtype(df['Amount']):
        df['Amount'] = (
            df['Amount']
            .astype(str)
            .str.replace(',', '', regex=False)
            .str.replace('₹', '', regex=False)
            .str.replace(' ', '', regex=False)
            .astype(float)
        )

    # Normalize InvoiceDate: parse any date format into ISO YYYY-MM-DD strings
    # so they merge cleanly into master (which stores dates as ISO strings)
    if 'InvoiceDate' in df.columns:
        parsed = pd.to_datetime(df['InvoiceDate'], errors='coerce')
        # Only overwrite if parsing succeeded (don't lose already-good dates)
        valid_mask = parsed.notna()
        df.loc[valid_mask, 'InvoiceDate'] = parsed[valid_mask].dt.strftime('%Y-%m-%d')

    return df


# =============================================================================
# MERGE LOGIC
# =============================================================================

def load_master():
    """Load existing master file, or return empty DataFrame."""
    if os.path.exists(MASTER_FILE):
        df = pd.read_csv(MASTER_FILE)
        print(f"📂 Loaded master: {len(df)} invoices")
        return df
    else:
        print("📂 No master file found — starting fresh")
        return pd.DataFrame()


def find_inbox_files():
    """Find all CSV files in the inbox directory (not in /processed)."""
    patterns = [
        os.path.join(INBOX_DIR, '*.csv'),
        os.path.join(INBOX_DIR, '*.CSV'),
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    return sorted(files)


def merge_new_invoices(master_df, inbox_files):
    """
    Read inbox CSVs, normalize columns, deduplicate against master by ID,
    and return the merged DataFrame + stats.
    """
    if not inbox_files:
        print("📭 No new files in inbox/")
        return master_df, {'files': 0, 'new_rows': 0, 'duplicates': 0}
    
    # Collect existing IDs for fast lookup
    existing_ids = set()
    if len(master_df) > 0 and 'ID' in master_df.columns:
        existing_ids = set(master_df['ID'].astype(str).unique())
    
    all_new = []
    total_read = 0
    
    for fpath in inbox_files:
        fname = os.path.basename(fpath)
        try:
            df = pd.read_csv(fpath)
            df = normalize_columns(df)
            total_read += len(df)
            
            if 'ID' not in df.columns:
                print(f"  ⚠️  {fname}: No 'ID' column — skipping (cannot deduplicate)")
                continue
            
            df['ID'] = df['ID'].astype(str)
            new_rows = df[~df['ID'].isin(existing_ids)]
            dupes = len(df) - len(new_rows)
            
            print(f"  📄 {fname}: {len(df)} rows → {len(new_rows)} new, {dupes} duplicates")
            
            # Add new IDs to the lookup set for cross-file dedup
            existing_ids.update(new_rows['ID'].unique())
            all_new.append(new_rows)
            
        except Exception as e:
            print(f"  ❌ {fname}: Failed to read — {e}")
    
    if not all_new:
        return master_df, {'files': len(inbox_files), 'new_rows': 0, 'duplicates': total_read}
    
    new_df = pd.concat(all_new, ignore_index=True)
    
    if len(master_df) > 0:
        # Align columns: use master's columns as base, add any new columns from inbox
        for col in new_df.columns:
            if col not in master_df.columns:
                master_df[col] = pd.NA
        for col in master_df.columns:
            if col not in new_df.columns:
                new_df[col] = pd.NA
        
        merged = pd.concat([master_df, new_df[master_df.columns]], ignore_index=True)
    else:
        merged = new_df
    
    stats = {
        'files': len(inbox_files),
        'new_rows': len(new_df),
        'duplicates': total_read - len(new_df),
    }
    
    return merged, stats


def archive_inbox_files(inbox_files):
    """Move processed inbox files to /inbox/processed with timestamp."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    for fpath in inbox_files:
        fname = os.path.basename(fpath)
        name, ext = os.path.splitext(fname)
        dest = os.path.join(PROCESSED_DIR, f"{name}_{timestamp}{ext}")
        shutil.move(fpath, dest)
        print(f"  📁 Archived: {fname} → inbox/processed/{os.path.basename(dest)}")


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def run_update(recompute_only=False, as_of_date=None):
    """Full update pipeline."""
    
    if as_of_date is None:
        from datetime import date as date_cls
        as_of_date = date_cls.today()
    
    print("=" * 70)
    print("  MRR UPDATE PIPELINE")
    print("=" * 70)
    print(f"  Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Master: {MASTER_FILE}")
    print(f"  Inbox:  {INBOX_DIR}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 70)
    
    # Step 1: Load master
    master_df = load_master()
    
    if not recompute_only:
        # Step 2: Find and merge inbox files
        inbox_files = find_inbox_files()
        
        if inbox_files:
            print(f"\n📥 Found {len(inbox_files)} file(s) in inbox:")
            merged_df, stats = merge_new_invoices(master_df, inbox_files)
            
            if stats['new_rows'] > 0:
                # Step 3: Save updated master
                merged_df.to_csv(MASTER_FILE, index=False)
                print(f"\n💾 Master updated: {len(merged_df)} total invoices (+{stats['new_rows']} new)")
                master_df = merged_df
            else:
                print(f"\n📭 No new invoices to add ({stats['duplicates']} duplicates found)")
            
            # Step 4: Archive inbox files
            print(f"\n📁 Archiving inbox files:")
            archive_inbox_files(inbox_files)
        else:
            print("\n📭 Inbox is empty — nothing to merge")
    else:
        print("\n🔄 Recompute-only mode — skipping inbox merge")
    
    # Step 5: Run MRR calculation
    if len(master_df) == 0:
        print("\n⚠️  No invoice data to process. Drop a CSV in inbox/ and try again.")
        return
    
    print("\n" + "─" * 70)
    print("  RUNNING MRR CALCULATION")
    print("─" * 70)
    
    # Import and run the MRR engine
    sys.path.insert(0, SCRIPT_DIR)
    from calculate_mrr import calculate_mrr
    
    try:
        monthly_df, client_df, invoice_df = calculate_mrr(MASTER_FILE, OUTPUT_DIR)
        
        print(f"\n  📊 output/monthly_summary.csv    ({len(monthly_df)} months)")
        print(f"  📊 output/client_summary.csv     ({len(client_df)} clients)")
        print(f"  📊 output/invoices_enriched.csv   ({len(invoice_df)} invoices)")
        
    except Exception as e:
        print(f"\n❌ MRR calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 6: Run projections
    print("\n" + "─" * 70)
    print("  RUNNING PROJECTIONS")
    print("─" * 70)
    
    try:
        sys.path.insert(0, BASE_DIR)
        from project_mrr import run_projections
        proj_df = run_projections(as_of_date=as_of_date)
        
        print("\n" + "─" * 70)
        print("  UPDATE COMPLETE")
        print("─" * 70)
        print("=" * 70)
        
    except Exception as e:
        print(f"\n⚠️  Projections failed (MRR data is still valid): {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    recompute = '--recompute-only' in sys.argv
    as_of = None
    for i, arg in enumerate(sys.argv):
        if arg == '--as-of-date' and i + 1 < len(sys.argv):
            from datetime import datetime as dt_cls
            as_of = dt_cls.strptime(sys.argv[i + 1], '%Y-%m-%d').date()
    run_update(recompute_only=recompute, as_of_date=as_of)
