import json
import logging
import os
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_INTELLIGENCE_PATH = (
    PROJECT_ROOT / "data" / "external" / "external_intelligence.json"
)

REQUIRED_FIELDS = [
    "intelligence_track",
    "entity_type",
    "entity_value",
    "search_query",
]

LOAD_COLUMNS = [
    "intelligence_track",
    "entity_type",
    "entity_value",
    "internal_metric_context",
    "search_query",
    "market_summary",
    "target_customer_segment",
    "business_recommendation",
    "risk_or_challenge",
    "source_titles",
    "source_urls",
]

CONFLICT_COLUMNS = [
    "intelligence_track",
    "entity_type",
    "entity_value",
    "search_query",
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


def load_json_items() -> list[dict[str, Any]]:
    if not EXTERNAL_INTELLIGENCE_PATH.exists():
        raise FileNotFoundError(
            f"Missing external intelligence file: {EXTERNAL_INTELLIGENCE_PATH}"
        )

    with EXTERNAL_INTELLIGENCE_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("External intelligence JSON must contain an items array.")

    return items


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def validate_item(item: Any) -> tuple[bool, str | None]:
    if not isinstance(item, dict):
        return False, "row is not a JSON object"

    missing_fields = [
        field for field in REQUIRED_FIELDS if is_blank(item.get(field))
    ]
    if missing_fields:
        return False, f"missing required field(s): {', '.join(missing_fields)}"

    for field in ["internal_metric_context", "source_titles", "source_urls"]:
        value = item.get(field)
        if value is not None and not isinstance(value, (dict, list)):
            return False, f"{field} must be a JSON object or array"

    return True, None


def prepare_records(
    items: list[dict[str, Any]],
) -> tuple[list[tuple[Any, ...]], int]:
    records = []
    skipped_rows = 0

    for index, item in enumerate(items, start=1):
        is_valid, reason = validate_item(item)
        if not is_valid:
            skipped_rows += 1
            logging.warning("Skipping JSON row %s: %s", index, reason)
            continue

        records.append(
            (
                item["intelligence_track"].strip(),
                item["entity_type"].strip(),
                item["entity_value"].strip(),
                Jsonb(item.get("internal_metric_context")),
                item["search_query"].strip(),
                item.get("market_summary"),
                item.get("target_customer_segment"),
                item.get("business_recommendation"),
                item.get("risk_or_challenge"),
                Jsonb(item.get("source_titles")),
                Jsonb(item.get("source_urls")),
            )
        )

    return records, skipped_rows


def count_existing_keys(
    conn: psycopg.Connection,
    records: list[tuple[Any, ...]],
) -> int:
    if not records:
        return 0

    existing_count = 0
    query = """
        SELECT 1
        FROM dim_external_intelligence
        WHERE intelligence_track = %s
          AND entity_type = %s
          AND entity_value = %s
          AND search_query = %s
        LIMIT 1
    """

    with conn.cursor() as cur:
        for record in records:
            cur.execute(
                query,
                (
                    record[0],
                    record[1],
                    record[2],
                    record[4],
                ),
            )
            if cur.fetchone() is not None:
                existing_count += 1

    return existing_count


def upsert_external_intelligence(
    conn: psycopg.Connection,
    records: list[tuple[Any, ...]],
) -> tuple[int, int]:
    existing_before = count_existing_keys(conn, records)
    if not records:
        return 0, 0

    placeholders = ", ".join(["%s"] * len(LOAD_COLUMNS))
    insert_columns = ", ".join(LOAD_COLUMNS)
    conflict_columns = ", ".join(CONFLICT_COLUMNS)
    update_columns = [
        column for column in LOAD_COLUMNS if column not in CONFLICT_COLUMNS
    ]
    update_assignments = ", ".join(
        f"{column} = EXCLUDED.{column}" for column in update_columns
    )

    query = f"""
        INSERT INTO dim_external_intelligence ({insert_columns})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_columns})
        DO UPDATE SET
            {update_assignments},
            updated_at = NOW()
    """

    with conn.cursor() as cur:
        cur.executemany(query, records)
        affected_rows = cur.rowcount

    inserted_rows = max(len(records) - existing_before, 0)
    updated_rows = max(affected_rows - inserted_rows, 0)
    return inserted_rows, updated_rows


def normalize_legacy_product_category_entity_type(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE dim_external_intelligence
            SET
                entity_type = 'product_category',
                updated_at = NOW()
            WHERE intelligence_track = 'product_category_market'
              AND entity_type = 'product_category_name_english'
            """
        )
        return cur.rowcount


def load_external_intelligence() -> None:
    items = load_json_items()
    records, skipped_rows = prepare_records(items)

    with get_connection() as conn:
        try:
            normalized_rows = normalize_legacy_product_category_entity_type(conn)
            if normalized_rows:
                logging.info(
                    "Normalized legacy product category intelligence rows: %s",
                    f"{normalized_rows:,}",
                )

            inserted_rows, updated_rows = upsert_external_intelligence(conn, records)
            conn.commit()
        except Exception:
            conn.rollback()
            logging.exception(
                "External intelligence load failed. Transaction rolled back."
            )
            raise

    print(f"Total JSON rows read: {len(items):,}")
    print(f"Inserted rows: {inserted_rows:,}")
    print(f"Updated rows: {updated_rows:,}")
    print(f"Skipped/invalid rows: {skipped_rows:,}")


def main() -> None:
    configure_logging()
    load_external_intelligence()


if __name__ == "__main__":
    main()
