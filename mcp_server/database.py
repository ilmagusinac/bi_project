import os
import re
from contextlib import contextmanager
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg import sql


load_dotenv()


BLOCKED_SQL_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "COPY",
    "GRANT",
    "REVOKE",
    "CALL",
    "DO",
    "EXECUTE",
}

PHYSICAL_WAREHOUSE_TABLES = {
    "dim_date",
    "dim_customer",
    "dim_product",
    "dim_seller",
    "dim_payment_summary",
    "dim_review",
    "dim_geolocation",
    "dim_external_intelligence",
    "fact_order_items",
}

APPROVED_ANALYTICAL_VIEWS = {
    "vw_sales_overview",
    "vw_monthly_revenue",
    "vw_product_category_performance",
    "vw_seller_performance",
    "vw_delivery_performance",
    "vw_customer_satisfaction",
    "vw_payment_analysis",
    "vw_geographic_revenue",
    "vw_product_category_intelligence",
    "vw_geographic_intelligence",
    "vw_delivery_intelligence",
}

SUPPORTED_RELATIONS = PHYSICAL_WAREHOUSE_TABLES | APPROVED_ANALYTICAL_VIEWS


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@contextmanager
def get_connection():
    conn = psycopg.connect(
        host=_required_env("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=_required_env("POSTGRES_DATABASE"),
        user=_required_env("POSTGRES_USER"),
        password=_required_env("POSTGRES_PASSWORD"),
        sslmode=os.getenv("POSTGRES_SSLMODE", "require"),
        row_factory=dict_row,
        options="-c default_transaction_read_only=on -c statement_timeout=15000",
    )
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return list(cur.fetchall())


def fetch_one(query: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
    rows = fetch_all(query, params)
    return rows[0] if rows else None


def list_tables() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT relation_schema, relation_name AS table_name, relation_type AS table_type
        FROM (
            SELECT table_schema AS relation_schema, table_name AS relation_name, table_type AS relation_type
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ANY(%s)

            UNION

            SELECT table_schema AS relation_schema, table_name AS relation_name, 'VIEW' AS relation_type
            FROM information_schema.views
            WHERE table_schema = 'public'
              AND table_name = ANY(%s)
        ) supported_relations
        ORDER BY table_name;
        """,
        (sorted(SUPPORTED_RELATIONS), sorted(SUPPORTED_RELATIONS)),
    )


def describe_table(table_name: str) -> dict[str, Any]:
    _validate_known_table(table_name)

    columns = fetch_all(
        """
        SELECT
            column_name,
            data_type,
            udt_name,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position;
        """,
        (table_name,),
    )

    constraints = fetch_all(
        """
        SELECT
            tc.constraint_name,
            tc.constraint_type,
            kcu.column_name
        FROM information_schema.table_constraints tc
        LEFT JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
           AND tc.table_schema = kcu.table_schema
           AND tc.table_name = kcu.table_name
        WHERE tc.table_schema = 'public'
          AND tc.table_name = %s
        ORDER BY tc.constraint_type, tc.constraint_name, kcu.ordinal_position;
        """,
        (table_name,),
    )

    return {
        "table_name": table_name,
        "columns": columns,
        "constraints": constraints,
    }


def get_schema() -> dict[str, Any]:
    relations = list_tables()
    return {
        "tables": relations,
        "relations": relations,
        "foreign_keys": get_foreign_keys(),
        "columns": fetch_all(
            """
            SELECT
                table_name,
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = ANY(%s)
            ORDER BY table_name, ordinal_position;
            """,
            (sorted(SUPPORTED_RELATIONS),),
        ),
    }


def get_foreign_keys() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT
            tc.constraint_name,
            tc.table_name AS source_table,
            kcu.column_name AS source_column,
            ccu.table_name AS target_table,
            ccu.column_name AS target_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
           AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
           AND ccu.table_schema = tc.table_schema
        WHERE tc.table_schema = 'public'
          AND tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_name = ANY(%s)
        ORDER BY tc.table_name, kcu.column_name;
        """,
        (sorted(PHYSICAL_WAREHOUSE_TABLES),),
    )


def run_readonly_sql(query: str) -> list[dict[str, Any]]:
    safe_query = build_safe_select(query)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(safe_query)
            return list(cur.fetchall())


def build_safe_select(query: str) -> str:
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("SQL query cannot be empty.")

    without_trailing_semicolon = cleaned_query[:-1].strip() if cleaned_query.endswith(";") else cleaned_query
    if ";" in without_trailing_semicolon:
        raise ValueError("Multiple SQL statements are not allowed.")

    sql_for_checks = _remove_comments_and_literals(without_trailing_semicolon)
    first_word = _first_keyword(sql_for_checks)
    if first_word != "SELECT":
        raise ValueError("Only SELECT queries are allowed.")

    blocked_found = sorted(
        keyword
        for keyword in BLOCKED_SQL_KEYWORDS
        if re.search(rf"\b{keyword}\b", sql_for_checks, flags=re.IGNORECASE)
    )
    if blocked_found:
        raise ValueError(
            "Blocked SQL keyword found: " + ", ".join(blocked_found)
        )

    if not re.search(r"\bLIMIT\b", sql_for_checks, flags=re.IGNORECASE):
        return f"{without_trailing_semicolon}\nLIMIT 100"

    return without_trailing_semicolon


def _validate_known_table(table_name: str) -> None:
    if table_name not in SUPPORTED_RELATIONS:
        valid_relations = ", ".join(sorted(SUPPORTED_RELATIONS))
        raise ValueError(
            f"Unknown or unsupported relation '{table_name}'. Valid relations: {valid_relations}"
        )


def _first_keyword(query: str) -> str | None:
    match = re.search(r"\b[A-Za-z_][A-Za-z0-9_]*\b", query)
    return match.group(0).upper() if match else None


def _remove_comments_and_literals(query: str) -> str:
    query = re.sub(r"--.*?$", " ", query, flags=re.MULTILINE)
    query = re.sub(r"/\*.*?\*/", " ", query, flags=re.DOTALL)
    query = re.sub(r"'(?:''|[^'])*'", "''", query)
    query = re.sub(r'"(?:""|[^"])*"', '""', query)
    return query


def table_row_count(table_name: str) -> int:
    _validate_known_table(table_name)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT count(*) AS row_count FROM {}").format(
                    sql.Identifier(table_name)
                )
            )
            row = cur.fetchone()
            return int(row["row_count"])
