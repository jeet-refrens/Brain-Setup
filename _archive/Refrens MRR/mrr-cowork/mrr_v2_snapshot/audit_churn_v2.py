#!/usr/bin/env python3
"""Independent churn audit for the v2 snapshot workspace."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"
DATA_FILE = BASE_DIR / "data" / "master_invoices_v2.csv"
MONTHLY_FILE = BASE_DIR / "output" / "monthly_summary.csv"
AUDIT_FILE = BASE_DIR / "output" / "churn_audit.csv"

sys.path.insert(0, str(SCRIPTS_DIR))

from calculate_mrr_v2 import (  # noqa: E402
    REACTIVATION_GRACE_MONTHS,
    SUSPENSE_CLIENT_ID,
    build_complete_snapshot_maps,
    build_effective_snapshot_maps,
    load_and_clean_invoices,
    month_key,
    parse_date,
    read_csv_rows,
)


def read_monthly_summary() -> Dict[str, Dict[str, str]]:
    rows, _ = read_csv_rows(MONTHLY_FILE)
    return {row["Month"]: row for row in rows}


def audit_churn_rows() -> List[Dict[str, object]]:
    monthly_summary = read_monthly_summary()
    reference_date = parse_date(max(monthly_summary.values(), key=lambda row: row["Snapshot_Date"])["Snapshot_Date"])
    invoices = load_and_clean_invoices(DATA_FILE)

    snapshot_dates, raw_snapshot_client_mrrs, _ = build_complete_snapshot_maps(invoices, reference_date)
    effective_snapshot_client_mrrs = build_effective_snapshot_maps(raw_snapshot_client_mrrs)

    month_names = [month_key(snapshot_date) for snapshot_date in snapshot_dates]
    audit_rows: List[Dict[str, object]] = []

    for index, month_name in enumerate(month_names):
        previous_name = month_names[index - 1] if index > 0 else None
        current_map = effective_snapshot_client_mrrs.get(month_name, {})
        previous_map = effective_snapshot_client_mrrs.get(previous_name, {}) if previous_name else {}
        churned_clients = 0
        churned_mrr = 0.0

        client_ids = sorted(
            {
                client
                for client in set(current_map) | set(previous_map)
                if client != SUSPENSE_CLIENT_ID
            }
        )
        for client in client_ids:
            current_mrr = current_map.get(client, 0.0)
            previous_mrr = previous_map.get(client, 0.0)
            if previous_mrr > 0 and current_mrr == 0:
                churned_clients += 1
                churned_mrr += previous_mrr

        reported = monthly_summary.get(month_name, {})
        reported_clients = int(float(reported.get("Churned_Clients", 0) or 0))
        reported_mrr = float(reported.get("Churned_MRR", 0) or 0)
        audit_rows.append(
            {
                "Month": month_name,
                "Grace_Months": REACTIVATION_GRACE_MONTHS,
                "Audited_Churned_Clients": churned_clients,
                "Reported_Churned_Clients": reported_clients,
                "Clients_Match": "TRUE" if churned_clients == reported_clients else "FALSE",
                "Audited_Churned_MRR": round(churned_mrr, 2),
                "Reported_Churned_MRR": round(reported_mrr, 2),
                "MRR_Match": "TRUE" if round(churned_mrr, 2) == round(reported_mrr, 2) else "FALSE",
            }
        )

    return audit_rows


def write_rows(rows: List[Dict[str, object]]) -> None:
    fieldnames = [
        "Month",
        "Grace_Months",
        "Audited_Churned_Clients",
        "Reported_Churned_Clients",
        "Clients_Match",
        "Audited_Churned_MRR",
        "Reported_Churned_MRR",
        "MRR_Match",
    ]
    with AUDIT_FILE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    rows = audit_churn_rows()
    write_rows(rows)
    mismatches = [row for row in rows if row["Clients_Match"] != "TRUE" or row["MRR_Match"] != "TRUE"]
    print(f"Audited {len(rows)} month(s).")
    print(f"Grace months: {REACTIVATION_GRACE_MONTHS}")
    print(f"Mismatched months: {len(mismatches)}")
    if mismatches:
        first = mismatches[0]
        print(
            "First mismatch:",
            first["Month"],
            first["Audited_Churned_Clients"],
            first["Reported_Churned_Clients"],
            first["Audited_Churned_MRR"],
            first["Reported_Churned_MRR"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

