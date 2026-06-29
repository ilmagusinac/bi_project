import logging
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "docs" / "load_validation_report.txt"

EXPECTED_ROW_COUNTS = {
    "dim_date": 755,
    "dim_geolocation": 19015,
    "dim_customer": 99441,
    "dim_product": 32951,
    "dim_seller": 3095,
    "dim_payment_summary": 99441,
    "dim_review": 98673,
    "fact_order_items": 112650,
}

EXPECTED_TOTALS = {
    "product_revenue": Decimal("13591643.70"),
    "freight_value": Decimal("2251909.54"),
    "total_revenue": Decimal("15843553.24"),
}

REVENUE_TOLERANCE = Decimal("0.01")

REQUIRED_FACT_KEYS = [
    "customer_sk",
    "product_sk",
    "seller_sk",
    "payment_summary_sk",
    "purchase_date_sk",
    "estimated_delivery_date_sk",
]

NULLABLE_FACT_KEYS = [
    "review_sk",
    "customer_geolocation_sk",
    "seller_geolocation_sk",
    "approved_date_sk",
    "delivered_carrier_date_sk",
    "delivered_customer_date_sk",
]


class ValidationReport:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.failures = 0

    def add(self, line: str = "") -> None:
        self.lines.append(line)

    def section(self, title: str) -> None:
        self.add("")
        self.add("=" * 80)
        self.add(title)
        self.add("=" * 80)

    def check(self, passed: bool, message: str) -> None:
        status = "PASS" if passed else "FAIL"
        self.add(f"[{status}] {message}")

        if not passed:
            self.failures += 1

    def text(self) -> str:
        return "\n".join(self.lines).strip() + "\n"


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_connection() -> psycopg.Connection:
    load_dotenv(PROJECT_ROOT / ".env")

    return psycopg.connect(
        host=required_env("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=required_env("POSTGRES_DATABASE"),
        user=required_env("POSTGRES_USER"),
        password=required_env("POSTGRES_PASSWORD"),
        sslmode=os.getenv("POSTGRES_SSLMODE", "require"),
        row_factory=dict_row,
        options="-c default_transaction_read_only=on",
    )


def fetch_one(conn: psycopg.Connection, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("Validation query returned no rows.")

    return dict(row)


def validate_row_counts(conn: psycopg.Connection, report: ValidationReport) -> None:
    report.section("Row Count Validation")

    for table_name, expected_count in EXPECTED_ROW_COUNTS.items():
        row = fetch_one(conn, f"SELECT COUNT(*) AS row_count FROM {table_name}")
        actual_count = int(row["row_count"])
        report.check(
            actual_count == expected_count,
            (
                f"{table_name}: expected {expected_count:,}, "
                f"actual {actual_count:,}"
            ),
        )


def validate_business_totals(conn: psycopg.Connection, report: ValidationReport) -> None:
    report.section("Business Total Validation")

    row = fetch_one(
        conn,
        """
        SELECT
            COALESCE(SUM(product_revenue), 0) AS product_revenue,
            COALESCE(SUM(freight_value), 0) AS freight_value,
            COALESCE(SUM(total_item_value), 0) AS total_revenue
        FROM fact_order_items
        """,
    )

    for metric_name, expected_value in EXPECTED_TOTALS.items():
        actual_value = Decimal(row[metric_name]).quantize(Decimal("0.01"))
        difference = abs(actual_value - expected_value)
        report.check(
            difference <= REVENUE_TOLERANCE,
            (
                f"{metric_name}: expected {expected_value:,.2f}, "
                f"actual {actual_value:,.2f}, difference {difference:,.2f}"
            ),
        )


def validate_required_keys(conn: psycopg.Connection, report: ValidationReport) -> None:
    report.section("Required Foreign Key Validation")

    for column in REQUIRED_FACT_KEYS:
        row = fetch_one(
            conn,
            f"""
            SELECT COUNT(*) AS missing_count
            FROM fact_order_items
            WHERE {column} IS NULL
            """,
        )
        missing_count = int(row["missing_count"])
        report.check(
            missing_count == 0,
            f"fact_order_items.{column} null count: {missing_count:,}",
        )


def validate_nullable_relationships(
    conn: psycopg.Connection,
    report: ValidationReport,
) -> None:
    report.section("Nullable Relationship Field Validation")

    for column in NULLABLE_FACT_KEYS:
        row = fetch_one(
            conn,
            f"""
            SELECT COUNT(*) AS null_count
            FROM fact_order_items
            WHERE {column} IS NULL
            """,
        )
        null_count = int(row["null_count"])
        report.check(
            True,
            f"fact_order_items.{column} nullable null count: {null_count:,}",
        )


def validate_delivery_metrics(conn: psycopg.Connection, report: ValidationReport) -> None:
    report.section("Delivery Metric Validation")

    row = fetch_one(
        conn,
        """
        SELECT
            COUNT(*) FILTER (WHERE is_late IS TRUE) AS late_delivery_count,
            AVG(CASE WHEN is_late THEN 1.0 ELSE 0.0 END) AS late_delivery_rate,
            AVG(delivery_days) AS average_delivery_days,
            AVG(delay_days) AS average_delay_days
        FROM fact_order_items
        """,
    )

    late_delivery_count = int(row["late_delivery_count"])
    late_delivery_rate = row["late_delivery_rate"]
    average_delivery_days = row["average_delivery_days"]
    average_delay_days = row["average_delay_days"]

    report.check(
        late_delivery_count >= 0,
        f"late delivery count: {late_delivery_count:,}",
    )
    report.check(
        late_delivery_rate is not None,
        f"late delivery rate: {float(late_delivery_rate):.4f}",
    )
    report.check(
        average_delivery_days is not None,
        f"average delivery_days: {float(average_delivery_days):.2f}",
    )
    report.check(
        average_delay_days is not None,
        f"average delay_days: {float(average_delay_days):.2f}",
    )


def validate_review_metric(conn: psycopg.Connection, report: ValidationReport) -> None:
    report.section("Review Metric Validation")

    row = fetch_one(
        conn,
        """
        SELECT AVG(review_score) AS average_review_score
        FROM dim_review
        """,
    )
    average_review_score = row["average_review_score"]

    report.check(
        average_review_score is not None,
        f"average review score: {float(average_review_score):.2f}",
    )


def run_validation() -> ValidationReport:
    report = ValidationReport()
    report.add("Olist Warehouse Load Validation Report")

    with get_connection() as conn:
        validate_row_counts(conn, report)
        validate_business_totals(conn, report)
        validate_required_keys(conn, report)
        validate_nullable_relationships(conn, report)
        validate_delivery_metrics(conn, report)
        validate_review_metric(conn, report)

    report.section("Overall Result")
    report.check(
        report.failures == 0,
        f"validation completed with {report.failures} failure(s)",
    )

    return report


def main() -> None:
    configure_logging()
    report = run_validation()
    report_text = report.text()

    print(report_text)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    logging.info("Validation report saved to %s", REPORT_PATH)


if __name__ == "__main__":
    main()
