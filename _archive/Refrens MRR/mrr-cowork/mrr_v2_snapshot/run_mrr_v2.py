#!/usr/bin/env python3
"""Runner for the isolated month-end snapshot MRR workspace."""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INBOX_DIR = BASE_DIR / "inbox"
PROCESSED_DIR = INBOX_DIR / "processed"
OUTPUT_DIR = BASE_DIR / "output"
MASTER_FILE = DATA_DIR / "master_invoices_v2.csv"
ROOT_MASTER_FILE = BASE_DIR.parent / "master_invoices.csv"
SCRIPTS_DIR = BASE_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

from calculate_mrr_v2 import canonicalize_header, calculate_mrr, read_csv_rows, write_csv_rows  # noqa: E402


def ensure_directories() -> None:
    for path in (DATA_DIR, INBOX_DIR, PROCESSED_DIR, OUTPUT_DIR, SCRIPTS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def bootstrap_master_copy() -> None:
    if MASTER_FILE.exists():
        return
    if not ROOT_MASTER_FILE.exists():
        raise FileNotFoundError(f"Missing source master file: {ROOT_MASTER_FILE}")
    shutil.copy2(ROOT_MASTER_FILE, MASTER_FILE)


def find_inbox_files() -> List[Path]:
    return sorted(
        path
        for pattern in ("*.csv", "*.CSV")
        for path in INBOX_DIR.glob(pattern)
        if path.is_file()
    )


def load_master_rows() -> Tuple[List[Dict[str, str]], List[str]]:
    if not MASTER_FILE.exists():
        return [], []
    return read_csv_rows(MASTER_FILE)


def merge_new_invoices(inbox_files: Sequence[Path]) -> Dict[str, int]:
    master_rows, master_headers = load_master_rows()
    existing_ids = {str(row.get("ID", "")).strip() for row in master_rows if str(row.get("ID", "")).strip()}
    all_headers = list(master_headers)
    new_rows: List[Dict[str, str]] = []
    total_read = 0

    for path in inbox_files:
        rows, headers = read_csv_rows(path)
        total_read += len(rows)

        for header in headers:
            canonical = canonicalize_header(header)
            if canonical not in all_headers:
                all_headers.append(canonical)

        for row in rows:
            invoice_id = str(row.get("ID", "")).strip()
            if not invoice_id:
                continue
            if invoice_id in existing_ids:
                continue
            existing_ids.add(invoice_id)
            new_rows.append(row)
            for header in row.keys():
                if header not in all_headers:
                    all_headers.append(header)

    if new_rows:
        combined_rows = master_rows + new_rows
        write_csv_rows(MASTER_FILE, all_headers, combined_rows)

    return {
        "files": len(inbox_files),
        "rows_read": total_read,
        "new_rows": len(new_rows),
        "duplicates": total_read - len(new_rows),
    }


def archive_inbox_files(inbox_files: Sequence[Path]) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for source in inbox_files:
        destination = PROCESSED_DIR / f"{source.stem}_{timestamp}{source.suffix}"
        shutil.move(str(source), str(destination))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the isolated month-end snapshot MRR pipeline.")
    parser.add_argument(
        "--recompute-only",
        action="store_true",
        help="Skip inbox ingestion and recompute from the local v2 master file.",
    )
    parser.add_argument(
        "--as-of-date",
        type=str,
        help="Optional YYYY-MM-DD snapshot date for monthly_snapshot.csv.",
    )
    return parser.parse_args()


def parse_as_of_date(raw: str | None) -> date | None:
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d").date()


def main() -> int:
    args = parse_args()
    ensure_directories()
    bootstrap_master_copy()
    as_of_date = parse_as_of_date(args.as_of_date)

    print("=" * 72)
    print("MRR V2 SNAPSHOT PIPELINE")
    print("=" * 72)
    print(f"Workspace: {BASE_DIR}")
    print(f"Master:    {MASTER_FILE}")
    print(f"Output:    {OUTPUT_DIR}")
    print("=" * 72)

    if not args.recompute_only:
        inbox_files = find_inbox_files()
        if inbox_files:
            stats = merge_new_invoices(inbox_files)
            archive_inbox_files(inbox_files)
            print(
                f"Ingested {stats['files']} file(s): {stats['new_rows']} new rows, "
                f"{stats['duplicates']} duplicates."
            )
        else:
            print("Inbox is empty. No ingestion performed.")
    else:
        print("Recompute-only mode enabled. Skipping inbox ingestion.")

    monthly_rows, client_rows, invoice_rows, snapshot_row = calculate_mrr(
        str(MASTER_FILE),
        str(OUTPUT_DIR),
        as_of_date=as_of_date,
    )

    print(f"Monthly history rows: {len(monthly_rows)}")
    print(f"Client summary rows:  {len(client_rows)}")
    print(f"Invoice rows:         {len(invoice_rows)}")
    if snapshot_row:
        print(
            "As-of snapshot:      "
            f"{snapshot_row['Snapshot_Date']} -> Total MRR {snapshot_row['Total_MRR']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

