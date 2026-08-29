import csv
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from calculate_mrr_v2 import calculate_mrr  # noqa: E402


FIXTURE = ROOT / "tests" / "fixtures" / "invoices_fixture.csv"
GRACE_FIXTURE = ROOT / "tests" / "fixtures" / "reactivation_grace_fixture.csv"
UPSELL_FIXTURE = ROOT / "tests" / "fixtures" / "same_product_upgrade_fixture.csv"


def read_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def row_by_month(rows, month_name):
    for row in rows:
        if row["Month"] == month_name:
            return row
    raise AssertionError(f"Missing month row: {month_name}")


class CalculateMRRV2Tests(unittest.TestCase):
    def run_engine(self, as_of_date: date, fixture: Path = FIXTURE):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "output"
            monthly_rows, client_rows, invoice_rows, snapshot_row = calculate_mrr(
                str(fixture),
                str(output_dir),
                as_of_date=as_of_date,
            )
            files = {
                "monthly": read_rows(output_dir / "monthly_summary.csv"),
                "clients": read_rows(output_dir / "client_summary.csv"),
                "invoices": read_rows(output_dir / "invoices_enriched.csv"),
                "snapshot": read_rows(output_dir / "monthly_snapshot.csv"),
            }
        return monthly_rows, client_rows, invoice_rows, snapshot_row, files

    def test_month_end_summary_and_suspense_separation(self):
        _, _, _, _, files = self.run_engine(date(2024, 3, 5))
        monthly = files["monthly"]

        self.assertEqual([row["Month"] for row in monthly], ["2024-01", "2024-02"])

        january = row_by_month(monthly, "2024-01")
        self.assertEqual(float(january["Core_MRR"]), 500.0)
        self.assertEqual(float(january["Suspense_MRR"]), 90.0)
        self.assertEqual(float(january["Total_MRR"]), 590.0)
        self.assertEqual(int(january["Active_Clients"]), 5)
        self.assertEqual(float(january["ARPU"]), 100.0)
        self.assertEqual(int(january["Inv_New_Clients"]), 5)

        february = row_by_month(monthly, "2024-02")
        self.assertEqual(float(february["Core_MRR"]), 650.0)
        self.assertEqual(float(february["Suspense_MRR"]), 0.0)
        self.assertEqual(float(february["New_MRR"]), 100.0)
        self.assertEqual(float(february["Expansion_MRR"]), 50.0)
        self.assertEqual(float(february["Churned_MRR"]), 0.0)
        self.assertEqual(float(february["NRR_Pct"]), 110.0)
        self.assertEqual(float(february["GRR_Pct"]), 100.0)
        self.assertEqual(float(february["Logo_Churn_Pct"]), 0.0)
        self.assertEqual(february["Quick_Ratio"], "")
        self.assertEqual(int(february["Active_Clients"]), 6)
        self.assertEqual(int(february["Clients_With_Invoices"]), 2)

    def test_snapshot_file_is_separate_from_monthly_history(self):
        _, _, _, snapshot_row, files = self.run_engine(date(2024, 3, 5))
        monthly = files["monthly"]
        snapshot = files["snapshot"]

        self.assertEqual(monthly[-1]["Month"], "2024-02")
        self.assertIsNotNone(snapshot_row)
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(snapshot[0]["Snapshot_Date"], "2024-03-05")
        self.assertEqual(snapshot[0]["Month"], "2024-03")
        self.assertEqual(float(snapshot[0]["Core_MRR"]), 450.0)
        self.assertEqual(float(snapshot[0]["Total_MRR"]), 450.0)
        self.assertEqual(int(snapshot[0]["Active_Clients"]), 4)

    def test_overlap_renewal_uses_latest_invoice_only(self):
        _, _, _, _, files = self.run_engine(date(2025, 1, 15))
        clients = files["clients"]
        renew = next(row for row in clients if row["ClientProfile"] == "C_RENEW")

        self.assertEqual(float(renew["Current_MRR"]), 200.0)
        self.assertEqual(float(renew["Latest_MRR"]), 200.0)
        self.assertEqual(renew["MRR_Trajectory"], "ACTIVE_EXPANDED")

    def test_zero_metrics_are_written_as_zero_not_blank(self):
        _, _, _, _, files = self.run_engine(date(2024, 4, 5))
        march = row_by_month(files["monthly"], "2024-03")

        self.assertEqual(float(march["Churned_MRR"]), 200.0)
        self.assertEqual(float(march["Quick_Ratio"]), 0.0)
        self.assertEqual(float(march["NRR_Pct"]), 69.23)
        self.assertEqual(float(march["GRR_Pct"]), 69.23)
        self.assertEqual(march["Quick_Ratio"], "0.0")

    def test_reactivation_requires_two_missed_month_ends(self):
        _, _, invoice_rows, _, files = self.run_engine(date(2024, 5, 5), fixture=GRACE_FIXTURE)
        monthly = files["monthly"]
        january = row_by_month(monthly, "2024-01")
        february = row_by_month(monthly, "2024-02")
        march = row_by_month(monthly, "2024-03")
        april = row_by_month(monthly, "2024-04")

        self.assertEqual(float(january["Core_MRR"]), 100.0)
        self.assertEqual(float(february["Core_MRR"]), 100.0)
        self.assertEqual(float(march["Core_MRR"]), 0.0)
        self.assertEqual(float(march["Churned_MRR"]), 100.0)
        self.assertEqual(float(april["Reactivation_MRR"]), 100.0)
        self.assertEqual(int(april["Reactivation_Clients"]), 1)

        gap_invoice = next(row for row in files["invoices"] if row["Invoice_ID"] == "g2")
        self.assertEqual(gap_invoice["Client_Month_End_Movement_Type"], "REACTIVATION")

    def test_same_product_mid_term_upgrade_reconstructs_run_rate(self):
        _, clients, _, _, files = self.run_engine(date(2024, 8, 5), fixture=UPSELL_FIXTURE)
        july = row_by_month(files["monthly"], "2024-07")
        upgrade_invoice = next(row for row in files["invoices"] if row["Invoice_ID"] == "u2")
        client_row = next(row for row in files["clients"] if row["ClientProfile"] == "C_UPSELL")

        self.assertEqual(float(upgrade_invoice["Invoice_MRR"]), 150.0)
        self.assertEqual(float(upgrade_invoice["Effective_Invoice_MRR"]), 200.0)
        self.assertEqual(upgrade_invoice["Overlap_Adjustment_Applied"], "TRUE")
        self.assertEqual(float(july["Core_MRR"]), 200.0)
        self.assertEqual(float(july["Expansion_MRR"]), 100.0)
        self.assertEqual(client_row["MRR_Trajectory"], "ACTIVE_EXPANDED")


if __name__ == "__main__":
    unittest.main()
