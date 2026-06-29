import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
import yaml
from dotenv import load_dotenv
from psycopg.rows import dict_row


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_QUERIES_PATH = PROJECT_ROOT / "agent_eval" / "golden_queries.yml"
REPORT_PATH = PROJECT_ROOT / "docs" / "golden_query_evaluation_report.txt"

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


@dataclass
class QueryResult:
    query_id: str
    business_question: str
    status: str
    row_count: int
    execution_time_seconds: float
    message: str


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


def load_golden_queries() -> list[dict[str, Any]]:
    with GOLDEN_QUERIES_PATH.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)

    queries = data.get("golden_queries", []) if data else []
    if not queries:
        raise RuntimeError(f"No golden queries found in {GOLDEN_QUERIES_PATH}")

    return queries


def remove_comments_and_literals(query: str) -> str:
    query = re.sub(r"--.*?$", " ", query, flags=re.MULTILINE)
    query = re.sub(r"/\*.*?\*/", " ", query, flags=re.DOTALL)
    query = re.sub(r"'(?:''|[^'])*'", "''", query)
    query = re.sub(r'"(?:""|[^"])*"', '""', query)
    return query


def first_keyword(query: str) -> str | None:
    match = re.search(r"\b[A-Za-z_][A-Za-z0-9_]*\b", query)
    return match.group(0).upper() if match else None


def validate_readonly_select(query: str) -> str:
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("SQL query is empty.")

    without_trailing_semicolon = (
        cleaned_query[:-1].strip()
        if cleaned_query.endswith(";")
        else cleaned_query
    )
    if ";" in without_trailing_semicolon:
        raise ValueError("Multiple SQL statements are not allowed.")

    sql_for_checks = remove_comments_and_literals(without_trailing_semicolon)
    if first_keyword(sql_for_checks) != "SELECT":
        raise ValueError("Only SELECT queries are allowed.")

    blocked_found = sorted(
        keyword
        for keyword in BLOCKED_SQL_KEYWORDS
        if re.search(rf"\b{keyword}\b", sql_for_checks, flags=re.IGNORECASE)
    )
    if blocked_found:
        raise ValueError("Blocked SQL keyword found: " + ", ".join(blocked_found))

    return without_trailing_semicolon


def execute_query(
    conn: psycopg.Connection,
    golden_query: dict[str, Any],
) -> QueryResult:
    query_id = golden_query["id"]
    business_question = golden_query["business_question"]
    expected_sql = golden_query["expected_sql"]

    start_time = time.perf_counter()
    try:
        safe_sql = validate_readonly_select(expected_sql)

        with conn.cursor() as cur:
            cur.execute(safe_sql)
            rows = cur.fetchall()

        execution_time = time.perf_counter() - start_time
        return QueryResult(
            query_id=query_id,
            business_question=business_question,
            status="PASS",
            row_count=len(rows),
            execution_time_seconds=execution_time,
            message="Query executed successfully.",
        )
    except Exception as error:
        execution_time = time.perf_counter() - start_time
        return QueryResult(
            query_id=query_id,
            business_question=business_question,
            status="FAIL",
            row_count=0,
            execution_time_seconds=execution_time,
            message=str(error),
        )


def build_report(results: list[QueryResult], total_time: float) -> str:
    passed = sum(1 for result in results if result.status == "PASS")
    failed = len(results) - passed
    lines = [
        "Golden Query Evaluation Report",
        "",
        f"Total queries: {len(results)}",
        f"Passed: {passed}",
        f"Failed: {failed}",
        f"Total execution time seconds: {total_time:.4f}",
        "",
        "=" * 80,
        "Query Results",
        "=" * 80,
    ]

    for result in results:
        lines.extend(
            [
                "",
                f"{result.query_id}: {result.status}",
                f"Business question: {result.business_question}",
                f"Rows returned: {result.row_count}",
                f"Execution time seconds: {result.execution_time_seconds:.4f}",
                f"Message: {result.message}",
            ]
        )

    return "\n".join(lines) + "\n"


def save_report(report_text: str) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report_text, encoding="utf-8")


def run_evaluation() -> tuple[list[QueryResult], float]:
    golden_queries = load_golden_queries()
    results: list[QueryResult] = []
    start_time = time.perf_counter()

    with get_connection() as conn:
        for golden_query in golden_queries:
            logging.info("Evaluating %s", golden_query["id"])
            result = execute_query(conn, golden_query)
            results.append(result)
            logging.info(
                "%s %s rows=%s time=%.4fs",
                result.query_id,
                result.status,
                result.row_count,
                result.execution_time_seconds,
            )

    total_time = time.perf_counter() - start_time
    return results, total_time


def main() -> None:
    configure_logging()
    results, total_time = run_evaluation()
    report_text = build_report(results, total_time)
    save_report(report_text)

    passed = sum(1 for result in results if result.status == "PASS")
    failed = len(results) - passed

    print("Golden query evaluation complete")
    print(f"Total queries: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Execution time seconds: {total_time:.4f}")
    print(f"Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
