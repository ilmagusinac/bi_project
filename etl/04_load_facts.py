import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
BATCH_SIZE = 5_000

ORDER_ITEMS_FILE = "olist_order_items_dataset.csv"
ORDERS_FILE = "olist_orders_dataset.csv"

ORDER_DATE_COLUMNS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

FACT_COLUMNS = [
    "order_id",
    "order_item_id",
    "customer_sk",
    "product_sk",
    "seller_sk",
    "payment_summary_sk",
    "review_sk",
    "customer_geolocation_sk",
    "seller_geolocation_sk",
    "purchase_date_sk",
    "approved_date_sk",
    "delivered_carrier_date_sk",
    "delivered_customer_date_sk",
    "estimated_delivery_date_sk",
    "order_status",
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
    "shipping_limit_date",
    "product_revenue",
    "freight_value",
    "total_item_value",
    "delivery_days",
    "estimated_delivery_days",
    "delay_days",
    "is_late",
]

REQUIRED_SURROGATE_KEYS = [
    "customer_sk",
    "product_sk",
    "seller_sk",
    "payment_summary_sk",
    "purchase_date_sk",
    "estimated_delivery_date_sk",
]

INTEGER_FACT_COLUMNS = [
    "order_item_id",
    "customer_sk",
    "product_sk",
    "seller_sk",
    "payment_summary_sk",
    "review_sk",
    "customer_geolocation_sk",
    "seller_geolocation_sk",
    "purchase_date_sk",
    "approved_date_sk",
    "delivered_carrier_date_sk",
    "delivered_customer_date_sk",
    "estimated_delivery_date_sk",
    "delivery_days",
    "estimated_delivery_days",
    "delay_days",
]


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
    )


def load_raw_order_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    order_items_path = RAW_DATA_DIR / ORDER_ITEMS_FILE
    orders_path = RAW_DATA_DIR / ORDERS_FILE

    if not order_items_path.exists():
        raise FileNotFoundError(f"Missing raw data file: {order_items_path}")
    if not orders_path.exists():
        raise FileNotFoundError(f"Missing raw data file: {orders_path}")

    order_items = pd.read_csv(order_items_path)
    orders = pd.read_csv(orders_path)

    order_items["shipping_limit_date"] = pd.to_datetime(
        order_items["shipping_limit_date"],
        errors="coerce",
    )

    for column in ORDER_DATE_COLUMNS:
        orders[column] = pd.to_datetime(orders[column], errors="coerce")

    return order_items, orders


def fetch_lookup(conn: psycopg.Connection, query: str) -> dict[Any, dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    return {row["lookup_key"]: dict(row) for row in rows}


def fetch_date_lookup(conn: psycopg.Connection) -> dict[Any, int]:
    with conn.cursor() as cur:
        cur.execute("SELECT full_date, date_sk FROM dim_date")
        rows = cur.fetchall()

    return {row["full_date"]: row["date_sk"] for row in rows}


def fetch_dimension_lookups(conn: psycopg.Connection) -> dict[str, dict[Any, Any]]:
    return {
        "customers": fetch_lookup(
            conn,
            """
            SELECT
                customer_id AS lookup_key,
                customer_sk,
                geolocation_sk AS customer_geolocation_sk
            FROM dim_customer
            """,
        ),
        "products": fetch_lookup(
            conn,
            """
            SELECT product_id AS lookup_key, product_sk
            FROM dim_product
            """,
        ),
        "sellers": fetch_lookup(
            conn,
            """
            SELECT
                seller_id AS lookup_key,
                seller_sk,
                geolocation_sk AS seller_geolocation_sk
            FROM dim_seller
            """,
        ),
        "payments": fetch_lookup(
            conn,
            """
            SELECT order_id AS lookup_key, payment_summary_sk
            FROM dim_payment_summary
            """,
        ),
        "reviews": fetch_lookup(
            conn,
            """
            SELECT order_id AS lookup_key, review_sk
            FROM dim_review
            """,
        ),
        "dates": fetch_date_lookup(conn),
    }


def date_part(series: pd.Series) -> pd.Series:
    return series.dt.date


def day_difference(end: pd.Series, start: pd.Series) -> pd.Series:
    return (end.dt.normalize() - start.dt.normalize()).dt.days


def prepare_fact_rows(
    order_items: pd.DataFrame,
    orders: pd.DataFrame,
    lookups: dict[str, dict[Any, Any]],
) -> tuple[pd.DataFrame, int]:
    joined = order_items.merge(
        orders,
        on="order_id",
        how="left",
        validate="many_to_one",
    )
    logging.info("Joined rows: %s", f"{len(joined):,}")

    customer_lookup = lookups["customers"]
    seller_lookup = lookups["sellers"]

    fact = joined.copy()
    fact["customer_sk"] = fact["customer_id"].map(
        lambda value: customer_lookup.get(value, {}).get("customer_sk")
    )
    fact["customer_geolocation_sk"] = fact["customer_id"].map(
        lambda value: customer_lookup.get(value, {}).get("customer_geolocation_sk")
    )
    fact["product_sk"] = fact["product_id"].map(
        lambda value: lookups["products"].get(value, {}).get("product_sk")
    )
    fact["seller_sk"] = fact["seller_id"].map(
        lambda value: seller_lookup.get(value, {}).get("seller_sk")
    )
    fact["seller_geolocation_sk"] = fact["seller_id"].map(
        lambda value: seller_lookup.get(value, {}).get("seller_geolocation_sk")
    )
    fact["payment_summary_sk"] = fact["order_id"].map(
        lambda value: lookups["payments"].get(value, {}).get("payment_summary_sk")
    )
    fact["review_sk"] = fact["order_id"].map(
        lambda value: lookups["reviews"].get(value, {}).get("review_sk")
    )

    date_lookup = lookups["dates"]
    fact["purchase_date_sk"] = date_part(fact["order_purchase_timestamp"]).map(
        date_lookup
    )
    fact["approved_date_sk"] = date_part(fact["order_approved_at"]).map(date_lookup)
    fact["delivered_carrier_date_sk"] = date_part(
        fact["order_delivered_carrier_date"]
    ).map(date_lookup)
    fact["delivered_customer_date_sk"] = date_part(
        fact["order_delivered_customer_date"]
    ).map(date_lookup)
    fact["estimated_delivery_date_sk"] = date_part(
        fact["order_estimated_delivery_date"]
    ).map(date_lookup)

    fact["product_revenue"] = fact["price"].round(2)
    fact["freight_value"] = fact["freight_value"].round(2)
    fact["total_item_value"] = (
        fact["product_revenue"] + fact["freight_value"]
    ).round(2)

    fact["delivery_days"] = day_difference(
        fact["order_delivered_customer_date"],
        fact["order_purchase_timestamp"],
    )
    fact["estimated_delivery_days"] = day_difference(
        fact["order_estimated_delivery_date"],
        fact["order_purchase_timestamp"],
    )
    fact["delay_days"] = day_difference(
        fact["order_delivered_customer_date"],
        fact["order_estimated_delivery_date"],
    )
    fact["is_late"] = (
        fact["order_delivered_customer_date"] > fact["order_estimated_delivery_date"]
    )
    fact["is_late"] = fact["is_late"].astype("boolean")
    fact.loc[fact["order_delivered_customer_date"].isna(), "is_late"] = pd.NA

    missing_required_keys = fact[REQUIRED_SURROGATE_KEYS].isna().any(axis=1)
    skipped_rows = int(missing_required_keys.sum())

    fact = fact.loc[~missing_required_keys, FACT_COLUMNS].copy()
    fact = fact.drop_duplicates(subset=["order_id", "order_item_id"])

    for column in INTEGER_FACT_COLUMNS:
        fact[column] = fact[column].astype("Int64")

    logging.info("Fact rows prepared: %s", f"{len(fact):,}")
    logging.info(
        "Rows skipped because required surrogate keys are missing: %s",
        f"{skipped_rows:,}",
    )

    return fact, skipped_rows


def clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if hasattr(value, "item"):
        return value.item()

    return value


def dataframe_records(df: pd.DataFrame) -> list[tuple[Any, ...]]:
    return [
        tuple(clean_value(value) for value in row)
        for row in df[FACT_COLUMNS].itertuples(index=False, name=None)
    ]


def batched(records: list[tuple[Any, ...]], batch_size: int) -> list[list[tuple[Any, ...]]]:
    return [
        records[start : start + batch_size]
        for start in range(0, len(records), batch_size)
    ]


def count_existing_fact_keys(
    conn: psycopg.Connection,
    fact: pd.DataFrame,
) -> int:
    order_ids = [clean_value(value) for value in fact["order_id"].dropna().unique()]

    if not order_ids:
        return 0

    prepared_keys = set(
        zip(
            fact["order_id"],
            fact["order_item_id"],
            strict=True,
        )
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT order_id, order_item_id
            FROM fact_order_items
            WHERE order_id = ANY(%s)
            """,
            (order_ids,),
        )
        existing_keys = {
            (row["order_id"], row["order_item_id"])
            for row in cur.fetchall()
        }

    return len(prepared_keys.intersection(existing_keys))


def upsert_fact_rows(
    conn: psycopg.Connection,
    fact: pd.DataFrame,
) -> tuple[int, int]:
    existing_before = count_existing_fact_keys(conn, fact)
    records = dataframe_records(fact)
    placeholders = ", ".join(["%s"] * len(FACT_COLUMNS))
    insert_columns = ", ".join(FACT_COLUMNS)
    update_columns = [
        column
        for column in FACT_COLUMNS
        if column not in {"order_id", "order_item_id"}
    ]
    update_assignments = ", ".join(
        f"{column} = EXCLUDED.{column}" for column in update_columns
    )

    query = f"""
        INSERT INTO fact_order_items ({insert_columns})
        VALUES ({placeholders})
        ON CONFLICT (order_id, order_item_id)
        DO UPDATE SET
            {update_assignments},
            updated_at = now()
    """

    affected_rows = 0
    with conn.cursor() as cur:
        for batch in batched(records, BATCH_SIZE):
            cur.executemany(query, batch)
            affected_rows += cur.rowcount

    inserted_rows = max(len(records) - existing_before, 0)
    updated_rows = max(affected_rows - inserted_rows, 0)
    return inserted_rows, updated_rows


def load_facts() -> None:
    order_items, orders = load_raw_order_data()
    logging.info("Raw order items: %s", f"{len(order_items):,}")

    with get_connection() as conn:
        try:
            lookups = fetch_dimension_lookups(conn)
            fact, _ = prepare_fact_rows(order_items, orders, lookups)
            inserted_rows, updated_rows = upsert_fact_rows(conn, fact)

            logging.info(
                "Fact rows inserted/updated: inserted=%s updated=%s",
                f"{inserted_rows:,}",
                f"{updated_rows:,}",
            )

            conn.commit()
            logging.info("Fact load committed successfully.")
        except Exception:
            conn.rollback()
            logging.exception("Fact load failed. Transaction rolled back.")
            raise


def main() -> None:
    configure_logging()
    load_facts()


if __name__ == "__main__":
    main()
