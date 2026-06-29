import importlib.util
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
from dotenv import load_dotenv
from psycopg import sql
from psycopg.rows import dict_row


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRANSFORM_MODULE_PATH = PROJECT_ROOT / "etl" / "02_transform_dimensions.py"
BATCH_SIZE = 5_000

LOAD_ORDER = [
    "dim_date",
    "dim_geolocation",
    "dim_customer",
    "dim_product",
    "dim_seller",
    "dim_payment_summary",
    "dim_review",
]


@dataclass(frozen=True)
class TableLoadConfig:
    table_name: str
    columns: list[str]
    conflict_columns: list[str]


TABLE_CONFIGS = {
    "dim_date": TableLoadConfig(
        table_name="dim_date",
        columns=[
            "full_date",
            "year",
            "quarter",
            "month",
            "month_name",
            "day",
            "day_of_week",
            "day_name",
            "week_of_year",
            "is_weekend",
        ],
        conflict_columns=["full_date"],
    ),
    "dim_geolocation": TableLoadConfig(
        table_name="dim_geolocation",
        columns=[
            "zip_code_prefix",
            "city",
            "state",
            "latitude",
            "longitude",
            "source_row_count",
        ],
        conflict_columns=["zip_code_prefix"],
    ),
    "dim_customer": TableLoadConfig(
        table_name="dim_customer",
        columns=[
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
            "geolocation_sk",
        ],
        conflict_columns=["customer_id"],
    ),
    "dim_product": TableLoadConfig(
        table_name="dim_product",
        columns=[
            "product_id",
            "product_category_name",
            "product_category_name_english",
            "product_name_length",
            "product_description_length",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
            "product_volume_cm3",
        ],
        conflict_columns=["product_id"],
    ),
    "dim_seller": TableLoadConfig(
        table_name="dim_seller",
        columns=[
            "seller_id",
            "seller_zip_code_prefix",
            "seller_city",
            "seller_state",
            "geolocation_sk",
        ],
        conflict_columns=["seller_id"],
    ),
    "dim_payment_summary": TableLoadConfig(
        table_name="dim_payment_summary",
        columns=[
            "order_id",
            "payment_count",
            "payment_type_count",
            "primary_payment_type",
            "max_payment_installments",
            "total_payment_value",
            "has_voucher",
            "has_credit_card",
            "has_boleto",
            "has_debit_card",
        ],
        conflict_columns=["order_id"],
    ),
    "dim_review": TableLoadConfig(
        table_name="dim_review",
        columns=[
            "order_id",
            "review_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
            "review_response_days",
            "review_count",
            "is_canonical_review",
        ],
        conflict_columns=["order_id"],
    ),
}


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


def load_transform_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "transform_dimensions",
        TRANSFORM_MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import transform module: {TRANSFORM_MODULE_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def transform_all_dimensions() -> dict[str, pd.DataFrame]:
    transform_module = load_transform_module()
    return transform_module.transform_all_dimensions()


def clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if hasattr(value, "item"):
        return value.item()

    return value


def dataframe_records(df: pd.DataFrame, columns: list[str]) -> list[tuple[Any, ...]]:
    return [
        tuple(clean_value(value) for value in row)
        for row in df[columns].itertuples(index=False, name=None)
    ]


def build_upsert_query(config: TableLoadConfig) -> sql.Composed:
    update_columns = [
        column
        for column in config.columns
        if column not in config.conflict_columns
    ]

    assignments = [
        sql.SQL("{} = EXCLUDED.{}").format(
            sql.Identifier(column),
            sql.Identifier(column),
        )
        for column in update_columns
    ]
    assignments.append(sql.SQL("updated_at = now()"))

    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in config.columns)

    return sql.SQL(
        """
        INSERT INTO {table} ({columns})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_columns})
        DO UPDATE SET {assignments}
        """
    ).format(
        table=sql.Identifier(config.table_name),
        columns=sql.SQL(", ").join(sql.Identifier(column) for column in config.columns),
        placeholders=placeholders,
        conflict_columns=sql.SQL(", ").join(
            sql.Identifier(column) for column in config.conflict_columns
        ),
        assignments=sql.SQL(", ").join(assignments),
    )


def batched(records: list[tuple[Any, ...]], batch_size: int) -> list[list[tuple[Any, ...]]]:
    return [
        records[start : start + batch_size]
        for start in range(0, len(records), batch_size)
    ]


def count_existing_keys(
    conn: psycopg.Connection,
    config: TableLoadConfig,
    df: pd.DataFrame,
) -> int:
    key_column = config.conflict_columns[0]
    key_values = [clean_value(value) for value in df[key_column].dropna().unique()]

    if not key_values:
        return 0

    query = sql.SQL("SELECT COUNT(*) AS row_count FROM {table} WHERE {key} = ANY(%s)").format(
        table=sql.Identifier(config.table_name),
        key=sql.Identifier(key_column),
    )

    with conn.cursor() as cur:
        cur.execute(query, (key_values,))
        return int(cur.fetchone()["row_count"])


def load_table(
    conn: psycopg.Connection,
    config: TableLoadConfig,
    df: pd.DataFrame,
) -> tuple[int, int]:
    existing_before = count_existing_keys(conn, config, df)
    records = dataframe_records(df, config.columns)
    query = build_upsert_query(config)
    affected_rows = 0

    with conn.cursor() as cur:
        for batch in batched(records, BATCH_SIZE):
            cur.executemany(query, batch)
            affected_rows += cur.rowcount

    inserted_rows = max(len(records) - existing_before, 0)
    updated_rows = max(affected_rows - inserted_rows, 0)
    return inserted_rows, updated_rows


def fetch_geolocation_lookup(conn: psycopg.Connection) -> dict[tuple[Any, str, str], int]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT geolocation_sk, zip_code_prefix, city, state
            FROM dim_geolocation
            """
        )
        rows = cur.fetchall()

    return {
        (
            row["zip_code_prefix"],
            row["city"],
            row["state"],
        ): row["geolocation_sk"]
        for row in rows
    }


def map_geolocation_keys(
    df: pd.DataFrame,
    lookup: dict[tuple[Any, str, str], int],
    zip_column: str,
    city_column: str,
    state_column: str,
) -> pd.DataFrame:
    mapped = df.copy()

    def lookup_key(row: pd.Series) -> int | None:
        key = (
            clean_value(row[zip_column]),
            clean_value(row[city_column]),
            clean_value(row[state_column]),
        )
        return lookup.get(key)

    mapped["geolocation_sk"] = mapped.apply(lookup_key, axis=1)
    return mapped


def load_dimensions() -> None:
    dimensions = transform_all_dimensions()

    with get_connection() as conn:
        try:
            for table_name in LOAD_ORDER:
                if table_name == "dim_customer":
                    lookup = fetch_geolocation_lookup(conn)
                    dimensions[table_name] = map_geolocation_keys(
                        dimensions[table_name],
                        lookup,
                        "customer_zip_code_prefix",
                        "customer_city",
                        "customer_state",
                    )
                elif table_name == "dim_seller":
                    lookup = fetch_geolocation_lookup(conn)
                    dimensions[table_name] = map_geolocation_keys(
                        dimensions[table_name],
                        lookup,
                        "seller_zip_code_prefix",
                        "seller_city",
                        "seller_state",
                    )

                inserted_rows, updated_rows = load_table(
                    conn,
                    TABLE_CONFIGS[table_name],
                    dimensions[table_name],
                )
                logging.info(
                    "%s loaded: inserted=%s updated=%s",
                    table_name,
                    f"{inserted_rows:,}",
                    f"{updated_rows:,}",
                )

            conn.commit()
            logging.info("Dimension load committed successfully.")
        except Exception:
            conn.rollback()
            logging.exception("Dimension load failed. Transaction rolled back.")
            raise


def main() -> None:
    configure_logging()
    load_dimensions()


if __name__ == "__main__":
    main()
