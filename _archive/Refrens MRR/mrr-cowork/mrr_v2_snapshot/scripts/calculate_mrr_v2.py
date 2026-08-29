#!/usr/bin/env python3
"""Month-end snapshot MRR engine for the isolated v2 workspace."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


PRODUCT_NAME_COLUMN = "Product \u2192 Name"
SUSPENSE_CLIENT_ID = "SUSPENSE_CLIENT"
REACTIVATION_GRACE_MONTHS = 2
SAME_PRODUCT_UPSELL_MIN_OVERLAP_DAYS = 60

PERIOD_MONTHS = {
    "WEEKLY": 0.25,
    "MONTHLY": 1,
    "QUARTERLY": 3,
    "QUATERLY": 3,
    "YEARLY": 12,
    "2YEARLY": 24,
    "3YEARLY": 36,
    "4YEARLY": 48,
    "5YEARLY": 60,
    "LIFETIME": 84,
}

HEADER_RENAMES = {
    "AmountInINR": "Amount",
    "InvoiceDate: Day": "InvoiceDate",
    "ProductName": PRODUCT_NAME_COLUMN,
}

MONTHLY_FIELDS = [
    "Month",
    "Snapshot_Date",
    "Core_MRR",
    "Suspense_MRR",
    "Total_MRR",
    "Total_ARR",
    "Active_Clients",
    "Beginning_MRR",
    "New_MRR",
    "Expansion_MRR",
    "Reactivation_MRR",
    "Contraction_MRR",
    "Churned_MRR",
    "Net_New_MRR",
    "New_Clients",
    "Expansion_Clients",
    "Reactivation_Clients",
    "Contraction_Clients",
    "Churned_Clients",
    "Clients_With_Invoices",
    "Inv_New_Clients",
    "Inv_Expansion_Clients",
    "Inv_Reactivation_Clients",
    "Inv_Contraction_Clients",
    "Inv_Churn_Clients",
    "Inv_Retained_Flat_Clients",
    "Inv_No_Month_End_MRR_Clients",
    "NRR_Pct",
    "GRR_Pct",
    "Logo_Churn_Pct",
    "Quick_Ratio",
    "ARPU",
    "Row_Type",
]

SNAPSHOT_FIELDS = [
    "Snapshot_Date",
    "Month",
    "Core_MRR",
    "Suspense_MRR",
    "Total_MRR",
    "Active_Clients",
    "ARPU",
    "Row_Type",
]

CLIENT_FIELDS = [
    "ClientProfile",
    "Status",
    "MRR_Trajectory",
    "Current_Plan",
    "Current_MRR",
    "Latest_MRR",
    "Avg_MRR",
    "Annualized_Run_Rate",
    "First_Period",
    "Latest_Period",
    "First_Product",
    "Latest_Product",
    "Renewal_Count",
    "Historical_Revenue",
    "Expansion_Revenue",
    "Total_Revenue",
    "Invoice_Count",
    "Has_Reactivated",
    "Churn_Count",
    "Reactivation_Count",
    "Account_Age_Months",
    "First_Invoice_Date",
    "Last_Invoice_Date",
    "First_Active_Month",
    "Last_Active_Month",
    "Months_Active",
    "Products",
]

INVOICE_FIELDS = [
    "Invoice_ID",
    "ClientProfile",
    "Product_ID",
    "Product_Name",
    "Period",
    "Invoice_Amount",
    "Invoice_Date",
    "Invoice_Month",
    "Subscription_Start",
    "Subscription_End_Exclusive",
    "Invoice_MRR",
    "Effective_Invoice_MRR",
    "Overlap_Adjustment_Applied",
    "Client_Prev_Month_End_MRR",
    "Client_Curr_Month_End_MRR",
    "Client_Month_End_MRR_Delta",
    "Client_First_Month_End",
    "Client_Month_End_Movement_Type",
]


@dataclass(frozen=True)
class InvoiceRecord:
    invoice_id: str
    client_profile: str
    product: str
    amount: float
    invoice_date: date
    period: str
    period_months: float
    normalized_mrr: float
    subscription_start: date
    subscription_end_exclusive: date
    product_name: str
    invoice_number: str
    effective_mrr: float
    overlap_adjustment_applied: bool


def canonicalize_header(header: str) -> str:
    return HEADER_RENAMES.get(header.strip(), header.strip())


def read_csv_rows(path: Path) -> Tuple[List[Dict[str, str]], List[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return [], []
        fieldnames = [canonicalize_header(name) for name in reader.fieldnames]
        rows: List[Dict[str, str]] = []
        for raw_row in reader:
            normalized: Dict[str, str] = {}
            for original_key, value in raw_row.items():
                if original_key is None:
                    continue
                normalized[canonicalize_header(original_key)] = value or ""
            rows.append(normalized)
    return rows, fieldnames


def write_csv_rows(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            cleaned = {}
            for field in fieldnames:
                value = row.get(field, "")
                cleaned[field] = "" if value is None else value
            writer.writerow(cleaned)


def normalize_amount(raw: str) -> float:
    text = (raw or "").strip()
    if not text:
        return 0.0
    cleaned = (
        text.replace(",", "")
        .replace("₹", "")
        .replace("$", "")
        .replace(" ", "")
    )
    return float(cleaned)


def parse_date(raw: str) -> date:
    text = (raw or "").strip()
    if not text:
        raise ValueError("Empty date value")

    candidates = [text]
    if "T" in text:
        candidates.append(text.split("T", 1)[0])

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%A, %B %d, %Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]

    for candidate in candidates:
        for fmt in formats:
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue

    try:
        return date.fromisoformat(candidates[-1])
    except ValueError as exc:
        raise ValueError(f"Unsupported date format: {text}") from exc


def add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = month_last_day(year, month).day
    day = min(start.day, last_day)
    return date(year, month, day)


def exact_months_between(start: date, end_exclusive: date) -> Optional[int]:
    if start >= end_exclusive:
        return 0
    months = (end_exclusive.year - start.year) * 12 + (end_exclusive.month - start.month)
    if add_months(start, months) == end_exclusive:
        return months
    return None


def derive_subscription_end_exclusive(start: date, period_months: float) -> date:
    if period_months < 1:
        return start + timedelta(days=int(period_months * 30))
    return add_months(start, int(period_months))


def month_start(day_value: date) -> date:
    return date(day_value.year, day_value.month, 1)


def month_last_day(year: int, month: int) -> date:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return next_month - timedelta(days=1)


def month_end(day_value: date) -> date:
    return month_last_day(day_value.year, day_value.month)


def previous_month_end(day_value: date) -> date:
    return month_start(day_value) - timedelta(days=1)


def month_key(day_value: date) -> str:
    return day_value.strftime("%Y-%m")


def round_currency(value: float) -> float:
    return round(value + 0.0, 2)


def round_percent(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 2)


def safe_ratio(numerator: float, denominator: float) -> Optional[float]:
    if denominator == 0:
        return None
    return numerator / denominator


def load_and_clean_invoices(filepath: Path) -> List[InvoiceRecord]:
    rows, _ = read_csv_rows(filepath)
    invoices: List[InvoiceRecord] = []

    for row in rows:
        invoice_id = str(row.get("ID", "")).strip()
        if not invoice_id:
            continue

        invoice_date = parse_date(row.get("InvoiceDate", ""))
        amount = normalize_amount(row.get("Amount", "0"))
        period = (row.get("Period", "") or "YEARLY").strip().upper()
        period_months = PERIOD_MONTHS.get(period, 12)
        normalized_mrr = amount / period_months
        client_profile = (row.get("ClientProfile", "") or "").strip() or SUSPENSE_CLIENT_ID
        product = (row.get("Product", "") or "").strip()
        product_name = (row.get(PRODUCT_NAME_COLUMN, "") or "").strip() or product
        invoice_number = (row.get("InvoiceNumber", "") or "").strip()

        raw_start = (row.get("SubscriptionStart", "") or "").strip()
        subscription_start = parse_date(raw_start) if raw_start else invoice_date

        raw_end = (row.get("SubscriptionEnd", "") or "").strip()
        if raw_end:
            subscription_end_exclusive = parse_date(raw_end)
        else:
            subscription_end_exclusive = derive_subscription_end_exclusive(subscription_start, period_months)

        if subscription_end_exclusive <= subscription_start:
            subscription_end_exclusive = derive_subscription_end_exclusive(subscription_start, period_months)

        invoices.append(
            InvoiceRecord(
                invoice_id=invoice_id,
                client_profile=client_profile,
                product=product,
                amount=amount,
                invoice_date=invoice_date,
                period=period,
                period_months=period_months,
                normalized_mrr=normalized_mrr,
                subscription_start=subscription_start,
                subscription_end_exclusive=subscription_end_exclusive,
                product_name=product_name,
                invoice_number=invoice_number,
                effective_mrr=normalized_mrr,
                overlap_adjustment_applied=False,
            )
        )

    invoices.sort(key=lambda record: (record.invoice_date, record.invoice_id))
    return build_effective_invoice_records(invoices)


def last_complete_month_end(reference_date: date) -> date:
    current_month_end = month_end(reference_date)
    if reference_date >= current_month_end:
        return current_month_end
    return previous_month_end(reference_date)


def iter_month_ends(start_day: date, end_day: date) -> List[date]:
    if start_day > end_day:
        return []
    cursor = month_end(start_day)
    months: List[date] = []
    while cursor <= end_day:
        months.append(cursor)
        next_month_start = cursor + timedelta(days=1)
        cursor = month_end(next_month_start)
    return months


def invoice_sort_key(record: InvoiceRecord) -> Tuple[date, str]:
    return (record.invoice_date, record.invoice_id)


def duration_days(start: date, end_exclusive: date) -> int:
    return max(0, (end_exclusive - start).days)


def overlapping_days(
    first_start: date,
    first_end_exclusive: date,
    second_start: date,
    second_end_exclusive: date,
) -> int:
    overlap_start = max(first_start, second_start)
    overlap_end = min(first_end_exclusive, second_end_exclusive)
    return max(0, (overlap_end - overlap_start).days)


def build_effective_invoice_records(invoices: Sequence[InvoiceRecord]) -> List[InvoiceRecord]:
    invoices_by_key: Dict[Tuple[str, str], List[InvoiceRecord]] = defaultdict(list)
    for record in invoices:
        invoices_by_key[(record.client_profile, record.product)].append(record)

    effective_records: List[InvoiceRecord] = []
    for records in invoices_by_key.values():
        records.sort(key=lambda record: (record.invoice_date, record.subscription_start, record.invoice_id))
        previous: Optional[InvoiceRecord] = None
        for record in records:
            effective_mrr = record.normalized_mrr
            adjustment_applied = False

            if previous is not None:
                is_mid_term_overlap = (
                    record.subscription_start > previous.subscription_start
                    and record.subscription_start < previous.subscription_end_exclusive
                )
                if is_mid_term_overlap:
                    record_day_count = duration_days(record.subscription_start, record.subscription_end_exclusive)
                    overlap_day_count = overlapping_days(
                        previous.subscription_start,
                        previous.subscription_end_exclusive,
                        record.subscription_start,
                        record.subscription_end_exclusive,
                    )
                    overlap_end_exclusive = min(
                        previous.subscription_end_exclusive, record.subscription_end_exclusive
                    )
                    exact_record_months = exact_months_between(
                        record.subscription_start, record.subscription_end_exclusive
                    )
                    exact_overlap_months = exact_months_between(
                        record.subscription_start, overlap_end_exclusive
                    )
                    if record_day_count > 0 and overlap_day_count >= SAME_PRODUCT_UPSELL_MIN_OVERLAP_DAYS:
                        overlap_months = (
                            float(exact_overlap_months)
                            if exact_overlap_months is not None
                            else overlap_day_count / 30.0
                        )
                        record_months = (
                            float(exact_record_months)
                            if exact_record_months is not None and exact_record_months > 0
                            else record_day_count / 30.0
                        )
                        reconstructed_mrr = (
                            record.amount + (previous.effective_mrr * overlap_months)
                        ) / record_months
                        if reconstructed_mrr > effective_mrr:
                            effective_mrr = reconstructed_mrr
                            adjustment_applied = True

            updated = InvoiceRecord(
                invoice_id=record.invoice_id,
                client_profile=record.client_profile,
                product=record.product,
                amount=record.amount,
                invoice_date=record.invoice_date,
                period=record.period,
                period_months=record.period_months,
                normalized_mrr=record.normalized_mrr,
                subscription_start=record.subscription_start,
                subscription_end_exclusive=record.subscription_end_exclusive,
                product_name=record.product_name,
                invoice_number=record.invoice_number,
                effective_mrr=effective_mrr,
                overlap_adjustment_applied=adjustment_applied,
            )
            effective_records.append(updated)
            previous = updated

    return sorted(effective_records, key=invoice_sort_key)


def build_snapshot_state(
    invoices: Sequence[InvoiceRecord], snapshot_date: date
) -> Tuple[Dict[str, float], Dict[Tuple[str, str], InvoiceRecord], Dict[str, List[InvoiceRecord]]]:
    latest_by_client_product: Dict[Tuple[str, str], InvoiceRecord] = {}

    for record in invoices:
        if record.subscription_start <= snapshot_date < record.subscription_end_exclusive:
            key = (record.client_profile, record.product)
            existing = latest_by_client_product.get(key)
            if existing is None or invoice_sort_key(record) > invoice_sort_key(existing):
                latest_by_client_product[key] = record

    client_mrr: Dict[str, float] = defaultdict(float)
    active_by_client: Dict[str, List[InvoiceRecord]] = defaultdict(list)

    for record in latest_by_client_product.values():
        client_mrr[record.client_profile] += record.effective_mrr
        active_by_client[record.client_profile].append(record)

    return dict(client_mrr), latest_by_client_product, dict(active_by_client)


def build_complete_snapshot_maps(
    invoices: Sequence[InvoiceRecord], reference_date: date
) -> Tuple[List[date], Dict[str, Dict[str, float]], Dict[str, Dict[str, List[InvoiceRecord]]]]:
    if not invoices:
        return [], {}, {}

    earliest_day = min(min(record.invoice_date, record.subscription_start) for record in invoices)
    latest_complete = last_complete_month_end(reference_date)
    if latest_complete < month_end(earliest_day):
        return [], {}, {}

    snapshot_dates = iter_month_ends(earliest_day, latest_complete)
    snapshot_client_mrrs: Dict[str, Dict[str, float]] = {}
    snapshot_active_products: Dict[str, Dict[str, List[InvoiceRecord]]] = {}

    for snapshot_date in snapshot_dates:
        key = month_key(snapshot_date)
        client_mrr, _, active_by_client = build_snapshot_state(invoices, snapshot_date)
        snapshot_client_mrrs[key] = client_mrr
        snapshot_active_products[key] = active_by_client

    return snapshot_dates, snapshot_client_mrrs, snapshot_active_products


def build_effective_snapshot_maps(
    raw_snapshot_client_mrrs: Dict[str, Dict[str, float]],
    grace_months: int = REACTIVATION_GRACE_MONTHS,
) -> Dict[str, Dict[str, float]]:
    month_names = sorted(raw_snapshot_client_mrrs.keys())
    clients = sorted(
        {
            client
            for month_name in month_names
            for client in raw_snapshot_client_mrrs.get(month_name, {})
        }
    )
    effective: Dict[str, Dict[str, float]] = {month_name: {} for month_name in month_names}

    for client in clients:
        if client == SUSPENSE_CLIENT_ID:
            for month_name in month_names:
                value = raw_snapshot_client_mrrs.get(month_name, {}).get(client, 0.0)
                if value > 0:
                    effective[month_name][client] = value
            continue

        last_active_mrr = 0.0
        inactive_streak = 0
        for month_name in month_names:
            raw_value = raw_snapshot_client_mrrs.get(month_name, {}).get(client, 0.0)
            if raw_value > 0:
                inactive_streak = 0
                last_active_mrr = raw_value
                effective[month_name][client] = raw_value
            elif last_active_mrr > 0:
                inactive_streak += 1
                if inactive_streak < grace_months:
                    effective[month_name][client] = last_active_mrr

    return effective


def build_first_active_month_map(snapshot_client_mrrs: Dict[str, Dict[str, float]]) -> Dict[str, str]:
    month_keys = sorted(snapshot_client_mrrs.keys())
    first_active: Dict[str, str] = {}
    for month_name in month_keys:
        for client, value in snapshot_client_mrrs[month_name].items():
            if client == SUSPENSE_CLIENT_ID or value <= 0:
                continue
            first_active.setdefault(client, month_name)
    return first_active


def classify_movement(
    client: str,
    month_name: str,
    snapshot_client_mrrs: Dict[str, Dict[str, float]],
    first_active_month_map: Dict[str, str],
) -> Tuple[str, float, float]:
    month_names = sorted(snapshot_client_mrrs.keys())
    current_index = month_names.index(month_name)
    previous_name = month_names[current_index - 1] if current_index > 0 else None

    current_mrr = snapshot_client_mrrs.get(month_name, {}).get(client, 0.0)
    previous_mrr = snapshot_client_mrrs.get(previous_name, {}).get(client, 0.0) if previous_name else 0.0

    if client == SUSPENSE_CLIENT_ID:
        return "SUSPENSE", previous_mrr, current_mrr
    if current_mrr > 0:
        if first_active_month_map.get(client) == month_name:
            return "NEW", previous_mrr, current_mrr
        if previous_mrr == 0:
            return "REACTIVATION", previous_mrr, current_mrr
        if current_mrr > previous_mrr:
            return "EXPANSION", previous_mrr, current_mrr
        if current_mrr < previous_mrr:
            return "CONTRACTION", previous_mrr, current_mrr
        return "RETAINED_FLAT", previous_mrr, current_mrr
    if previous_mrr > 0:
        return "CHURN", previous_mrr, current_mrr
    return "NO_MONTH_END_MRR", previous_mrr, current_mrr


def get_raw_inactive_streak_before_month(
    client: str,
    month_name: str,
    raw_snapshot_client_mrrs: Dict[str, Dict[str, float]],
) -> int:
    month_names = sorted(raw_snapshot_client_mrrs.keys())
    current_index = month_names.index(month_name)
    streak = 0
    for index in range(current_index - 1, -1, -1):
        previous_name = month_names[index]
        previous_value = raw_snapshot_client_mrrs.get(previous_name, {}).get(client, 0.0)
        if previous_value > 0:
            break
        streak += 1
    return streak


def build_monthly_summary_rows(
    snapshot_dates: Sequence[date],
    snapshot_client_mrrs: Dict[str, Dict[str, float]],
    first_active_month_map: Dict[str, str],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    month_names = [month_key(snapshot_date) for snapshot_date in snapshot_dates]

    for index, snapshot_date in enumerate(snapshot_dates):
        month_name = month_names[index]
        previous_name = month_names[index - 1] if index > 0 else None
        current_map = snapshot_client_mrrs.get(month_name, {})
        previous_map = snapshot_client_mrrs.get(previous_name, {}) if previous_name else {}

        current_core = {k: v for k, v in current_map.items() if k != SUSPENSE_CLIENT_ID and v > 0}
        previous_core = {k: v for k, v in previous_map.items() if k != SUSPENSE_CLIENT_ID and v > 0}
        all_clients = sorted(set(current_core) | set(previous_core))

        new_mrr = expansion_mrr = reactivation_mrr = 0.0
        contraction_mrr = churned_mrr = 0.0
        new_clients = expansion_clients = reactivation_clients = 0
        contraction_clients = churned_clients = 0

        for client in all_clients:
            movement, previous_mrr, current_mrr = classify_movement(
                client, month_name, snapshot_client_mrrs, first_active_month_map
            )
            if movement == "NEW":
                new_mrr += current_mrr
                new_clients += 1
            elif movement == "REACTIVATION":
                reactivation_mrr += current_mrr
                reactivation_clients += 1
            elif movement == "EXPANSION":
                expansion_mrr += current_mrr - previous_mrr
                expansion_clients += 1
            elif movement == "CONTRACTION":
                contraction_mrr += previous_mrr - current_mrr
                contraction_clients += 1
            elif movement == "CHURN":
                churned_mrr += previous_mrr
                churned_clients += 1

        core_mrr = sum(current_core.values())
        suspense_mrr = current_map.get(SUSPENSE_CLIENT_ID, 0.0)
        total_mrr = core_mrr + suspense_mrr
        beginning_mrr = sum(previous_core.values()) if previous_name else 0.0
        net_new_mrr = new_mrr + expansion_mrr + reactivation_mrr - contraction_mrr - churned_mrr

        nrr = None
        grr = None
        logo_churn = None
        if beginning_mrr > 0:
            nrr = ((beginning_mrr + expansion_mrr - contraction_mrr - churned_mrr) / beginning_mrr) * 100
            grr = ((beginning_mrr - contraction_mrr - churned_mrr) / beginning_mrr) * 100
            logo_churn = (churned_clients / len(previous_core)) * 100 if previous_core else None

        gross_add = new_mrr + expansion_mrr + reactivation_mrr
        gross_loss = contraction_mrr + churned_mrr
        quick_ratio = safe_ratio(gross_add, gross_loss)
        arpu = safe_ratio(core_mrr, len(current_core)) or 0.0

        rows.append(
            {
                "Month": month_name,
                "Snapshot_Date": snapshot_date.isoformat(),
                "Core_MRR": round_currency(core_mrr),
                "Suspense_MRR": round_currency(suspense_mrr),
                "Total_MRR": round_currency(total_mrr),
                "Total_ARR": round_currency(total_mrr * 12),
                "Active_Clients": len(current_core),
                "Beginning_MRR": round_currency(beginning_mrr),
                "New_MRR": round_currency(new_mrr),
                "Expansion_MRR": round_currency(expansion_mrr),
                "Reactivation_MRR": round_currency(reactivation_mrr),
                "Contraction_MRR": round_currency(contraction_mrr),
                "Churned_MRR": round_currency(churned_mrr),
                "Net_New_MRR": round_currency(net_new_mrr),
                "New_Clients": new_clients,
                "Expansion_Clients": expansion_clients,
                "Reactivation_Clients": reactivation_clients,
                "Contraction_Clients": contraction_clients,
                "Churned_Clients": churned_clients,
                "Clients_With_Invoices": 0,
                "Inv_New_Clients": 0,
                "Inv_Expansion_Clients": 0,
                "Inv_Reactivation_Clients": 0,
                "Inv_Contraction_Clients": 0,
                "Inv_Churn_Clients": 0,
                "Inv_Retained_Flat_Clients": 0,
                "Inv_No_Month_End_MRR_Clients": 0,
                "NRR_Pct": round_percent(nrr),
                "GRR_Pct": round_percent(grr),
                "Logo_Churn_Pct": round_percent(logo_churn),
                "Quick_Ratio": round_percent(quick_ratio),
                "ARPU": round_currency(arpu),
                "Row_Type": "ACTUAL_MONTH_END",
            }
        )

    return rows


def build_invoice_enriched_rows(
    invoices: Sequence[InvoiceRecord],
    snapshot_client_mrrs: Dict[str, Dict[str, float]],
    raw_snapshot_client_mrrs: Dict[str, Dict[str, float]],
    first_active_month_map: Dict[str, str],
) -> List[Dict[str, object]]:
    month_names = sorted(snapshot_client_mrrs.keys())
    available_months = set(month_names)
    invoice_rows: List[Dict[str, object]] = []

    for record in invoices:
        invoice_month_name = month_key(record.invoice_date)
        if record.client_profile == SUSPENSE_CLIENT_ID:
            movement = "SUSPENSE"
            previous_mrr = 0.0
            current_mrr = 0.0
        elif invoice_month_name not in available_months:
            movement = "PENDING_MONTH_END"
            previous_mrr = 0.0
            current_mrr = 0.0
        else:
            movement, previous_mrr, current_mrr = classify_movement(
                record.client_profile,
                invoice_month_name,
                snapshot_client_mrrs,
                first_active_month_map,
            )
            if movement == "REACTIVATION":
                raw_gap = get_raw_inactive_streak_before_month(
                    record.client_profile, invoice_month_name, raw_snapshot_client_mrrs
                )
                if raw_gap < REACTIVATION_GRACE_MONTHS:
                    movement = "RETURNED_WITHIN_GRACE"

        invoice_rows.append(
            {
                "Invoice_ID": record.invoice_id,
                "ClientProfile": record.client_profile,
                "Product_ID": record.product,
                "Product_Name": record.product_name,
                "Period": record.period,
                "Invoice_Amount": round_currency(record.amount),
                "Invoice_Date": record.invoice_date.isoformat(),
                "Invoice_Month": invoice_month_name,
                "Subscription_Start": record.subscription_start.isoformat(),
                "Subscription_End_Exclusive": record.subscription_end_exclusive.isoformat(),
                "Invoice_MRR": round_currency(record.normalized_mrr),
                "Effective_Invoice_MRR": round_currency(record.effective_mrr),
                "Overlap_Adjustment_Applied": "TRUE" if record.overlap_adjustment_applied else "FALSE",
                "Client_Prev_Month_End_MRR": round_currency(previous_mrr),
                "Client_Curr_Month_End_MRR": round_currency(current_mrr),
                "Client_Month_End_MRR_Delta": round_currency(current_mrr - previous_mrr),
                "Client_First_Month_End": first_active_month_map.get(record.client_profile, ""),
                "Client_Month_End_Movement_Type": movement,
            }
        )

    return invoice_rows


def apply_invoice_counts(
    monthly_rows: List[Dict[str, object]], invoice_rows: Sequence[Dict[str, object]]
) -> None:
    grouped: Dict[str, Dict[str, set]] = defaultdict(lambda: defaultdict(set))

    for row in invoice_rows:
        client = str(row["ClientProfile"])
        if client == SUSPENSE_CLIENT_ID:
            continue
        month_name = str(row["Invoice_Month"])
        movement = str(row["Client_Month_End_Movement_Type"])
        grouped[month_name]["ALL"].add(client)
        grouped[month_name][movement].add(client)

    for row in monthly_rows:
        month_name = str(row["Month"])
        movement_groups = grouped.get(month_name, {})
        row["Clients_With_Invoices"] = len(movement_groups.get("ALL", set()))
        row["Inv_New_Clients"] = len(movement_groups.get("NEW", set()))
        row["Inv_Expansion_Clients"] = len(movement_groups.get("EXPANSION", set()))
        row["Inv_Reactivation_Clients"] = len(movement_groups.get("REACTIVATION", set()))
        row["Inv_Contraction_Clients"] = len(movement_groups.get("CONTRACTION", set()))
        row["Inv_Churn_Clients"] = len(movement_groups.get("CHURN", set()))
        row["Inv_Retained_Flat_Clients"] = len(movement_groups.get("RETAINED_FLAT", set()))
        row["Inv_No_Month_End_MRR_Clients"] = len(movement_groups.get("NO_MONTH_END_MRR", set()))


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def build_client_summary_rows(
    invoices: Sequence[InvoiceRecord],
    snapshot_dates: Sequence[date],
    snapshot_client_mrrs: Dict[str, Dict[str, float]],
    raw_snapshot_client_mrrs: Dict[str, Dict[str, float]],
    snapshot_active_products: Dict[str, Dict[str, List[InvoiceRecord]]],
    first_active_month_map: Dict[str, str],
    reference_date: date,
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    if not snapshot_dates:
        return rows

    month_names = [month_key(snapshot_date) for snapshot_date in snapshot_dates]
    latest_month_name = month_names[-1]
    latest_snapshot_products = snapshot_active_products.get(latest_month_name, {})

    invoices_by_client: Dict[str, List[InvoiceRecord]] = defaultdict(list)
    for record in invoices:
        if record.client_profile != SUSPENSE_CLIENT_ID:
            invoices_by_client[record.client_profile].append(record)

    for client, client_invoices in sorted(invoices_by_client.items()):
        client_invoices.sort(key=invoice_sort_key)
        history = [snapshot_client_mrrs.get(month_name, {}).get(client, 0.0) for month_name in month_names]
        active_points = [value for value in history if value > 0]
        if not active_points:
            continue

        current_mrr = history[-1]
        latest_mrr = next(value for value in reversed(history) if value > 0)
        avg_mrr = sum(active_points) / len(active_points)
        previous_mrr = history[-2] if len(history) > 1 else 0.0
        raw_gap = get_raw_inactive_streak_before_month(client, latest_month_name, raw_snapshot_client_mrrs)

        if current_mrr == 0:
            trajectory = "CHURNED"
            status = "CHURNED"
        elif first_active_month_map.get(client) == latest_month_name:
            trajectory = "NEW"
            status = "ACTIVE"
        elif previous_mrr == 0 and raw_gap >= REACTIVATION_GRACE_MONTHS:
            trajectory = "REACTIVATED"
            status = "ACTIVE"
        elif current_mrr > previous_mrr:
            trajectory = "ACTIVE_EXPANDED"
            status = "ACTIVE"
        elif current_mrr < previous_mrr:
            trajectory = "ACTIVE_CONTRACTED"
            status = "ACTIVE"
        else:
            trajectory = "ACTIVE_STABLE"
            status = "ACTIVE"

        first_invoice = client_invoices[0]
        latest_invoice = client_invoices[-1]
        total_revenue = sum(record.amount for record in client_invoices)
        invoice_count = len(client_invoices)
        renewal_count = max(0, invoice_count - 1)

        expansion_revenue = 0.0
        for index in range(1, invoice_count):
            current_invoice = client_invoices[index]
            previous_invoice = client_invoices[index - 1]
            delta = current_invoice.normalized_mrr - previous_invoice.normalized_mrr
            if delta > 0:
                expansion_revenue += delta * current_invoice.period_months

        churn_count = 0
        reactivation_count = 0
        previous_value = 0.0
        was_ever_active = False
        for value in history:
            if value > 0 and previous_value == 0 and was_ever_active:
                reactivation_count += 1
            if value == 0 and previous_value > 0:
                churn_count += 1
            if value > 0:
                was_ever_active = True
            previous_value = value

        current_active_records = latest_snapshot_products.get(client, [])
        if current_active_records:
            active_names = sorted({record.product_name for record in current_active_records})
            current_plan = ", ".join(active_names[:3])
        else:
            current_plan = latest_invoice.product_name

        first_active_index = next(index for index, value in enumerate(history) if value > 0)
        last_active_index = max(index for index, value in enumerate(history) if value > 0)
        first_active_month = month_names[first_active_index]
        last_active_month = month_names[last_active_index]

        all_products = sorted({record.product_name for record in client_invoices if record.product_name})
        rows.append(
            {
                "ClientProfile": client,
                "Status": status,
                "MRR_Trajectory": trajectory,
                "Current_Plan": current_plan,
                "Current_MRR": round_currency(current_mrr),
                "Latest_MRR": round_currency(latest_mrr),
                "Avg_MRR": round_currency(avg_mrr),
                "Annualized_Run_Rate": round_currency(current_mrr * 12),
                "First_Period": first_invoice.period,
                "Latest_Period": latest_invoice.period,
                "First_Product": first_invoice.product_name,
                "Latest_Product": latest_invoice.product_name,
                "Renewal_Count": renewal_count,
                "Historical_Revenue": round_currency(total_revenue),
                "Expansion_Revenue": round_currency(expansion_revenue),
                "Total_Revenue": round_currency(total_revenue),
                "Invoice_Count": invoice_count,
                "Has_Reactivated": "TRUE" if reactivation_count > 0 else "FALSE",
                "Churn_Count": churn_count,
                "Reactivation_Count": reactivation_count,
                "Account_Age_Months": months_between(first_invoice.invoice_date, reference_date),
                "First_Invoice_Date": first_invoice.invoice_date.isoformat(),
                "Last_Invoice_Date": latest_invoice.invoice_date.isoformat(),
                "First_Active_Month": first_active_month,
                "Last_Active_Month": last_active_month,
                "Months_Active": len(active_points),
                "Products": ", ".join(all_products[:5]),
            }
        )

    return rows


def build_snapshot_output_row(
    invoices: Sequence[InvoiceRecord], snapshot_date: date
) -> Dict[str, object]:
    client_mrr, _, _ = build_snapshot_state(invoices, snapshot_date)
    core_mrr = sum(value for client, value in client_mrr.items() if client != SUSPENSE_CLIENT_ID)
    suspense_mrr = client_mrr.get(SUSPENSE_CLIENT_ID, 0.0)
    active_clients = sum(1 for client, value in client_mrr.items() if client != SUSPENSE_CLIENT_ID and value > 0)
    arpu = safe_ratio(core_mrr, active_clients) or 0.0
    return {
        "Snapshot_Date": snapshot_date.isoformat(),
        "Month": month_key(snapshot_date),
        "Core_MRR": round_currency(core_mrr),
        "Suspense_MRR": round_currency(suspense_mrr),
        "Total_MRR": round_currency(core_mrr + suspense_mrr),
        "Active_Clients": active_clients,
        "ARPU": round_currency(arpu),
        "Row_Type": "AS_OF_SNAPSHOT",
    }


def calculate_mrr(
    input_filepath: str,
    output_dir: str,
    as_of_date: Optional[date] = None,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], List[Dict[str, object]], Optional[Dict[str, object]]]:
    reference_date = as_of_date or date.today()
    invoices = load_and_clean_invoices(Path(input_filepath))
    snapshot_dates, raw_snapshot_client_mrrs, snapshot_active_products = build_complete_snapshot_maps(
        invoices, reference_date
    )
    snapshot_client_mrrs = build_effective_snapshot_maps(raw_snapshot_client_mrrs)
    first_active_month_map = build_first_active_month_map(snapshot_client_mrrs)

    monthly_rows = build_monthly_summary_rows(snapshot_dates, snapshot_client_mrrs, first_active_month_map)
    invoice_rows = build_invoice_enriched_rows(
        invoices, snapshot_client_mrrs, raw_snapshot_client_mrrs, first_active_month_map
    )
    apply_invoice_counts(monthly_rows, invoice_rows)
    client_rows = build_client_summary_rows(
        invoices,
        snapshot_dates,
        snapshot_client_mrrs,
        raw_snapshot_client_mrrs,
        snapshot_active_products,
        first_active_month_map,
        reference_date=last_complete_month_end(reference_date) if snapshot_dates else reference_date,
    )

    output_path = Path(output_dir)
    write_csv_rows(output_path / "monthly_summary.csv", MONTHLY_FIELDS, monthly_rows)
    write_csv_rows(output_path / "client_summary.csv", CLIENT_FIELDS, client_rows)
    write_csv_rows(output_path / "invoices_enriched.csv", INVOICE_FIELDS, invoice_rows)

    snapshot_row: Optional[Dict[str, object]] = None
    if as_of_date is not None:
        snapshot_row = build_snapshot_output_row(invoices, as_of_date)
        write_csv_rows(output_path / "monthly_snapshot.csv", SNAPSHOT_FIELDS, [snapshot_row])

    return monthly_rows, client_rows, invoice_rows, snapshot_row
