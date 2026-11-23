"""PostgreSQL connection and read-only query execution."""

import os
import re
from contextlib import closing
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
import sqlparse
from sqlparse import tokens as sql_tokens

load_dotenv(Path(__file__).with_name(".env"))

_SELECT_START = re.compile(r"^SELECT\b", re.IGNORECASE)
_BLOCKED_KEYWORDS = {
    "ALTER",
    "DELETE",
    "DROP",
    "INSERT",
    "TRUNCATE",
    "UPDATE",
}


class UnsafeQueryError(ValueError):
    """Raised when a generated query is not a single read-only SELECT."""


class DatabaseConfigurationError(RuntimeError):
    """Raised when the database environment is incomplete."""


def _connect() -> psycopg2.extensions.connection:
    required = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise DatabaseConfigurationError(
            f"Missing database environment variables: {', '.join(missing)}"
        )

    return psycopg2.connect(
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
    )


def validate_select_query(query: str) -> str:
    """Require one SELECT statement and reject destructive keywords."""
    if not query or not query.strip():
        raise UnsafeQueryError("SQL query must not be empty.")

    normalized = query.strip()
    if not _SELECT_START.match(normalized):
        raise UnsafeQueryError("Only SQL beginning with SELECT is allowed.")

    statements = [statement for statement in sqlparse.parse(normalized) if str(statement).strip()]
    if len(statements) != 1 or statements[0].get_type() != "SELECT":
        raise UnsafeQueryError("Exactly one SELECT statement is allowed.")

    def reject_destructive_tokens(token_list: Any) -> None:
        for token in token_list.tokens:
            if token.ttype in (sql_tokens.Keyword.DML, sql_tokens.Keyword.DDL):
                keyword = token.normalized.upper()
                if keyword in _BLOCKED_KEYWORDS:
                    raise UnsafeQueryError(f"Prohibited SQL operation: {keyword}.")
            if token.is_group:
                reject_destructive_tokens(token)

    reject_destructive_tokens(statements[0])
    return normalized


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def execute_query(query: str) -> list[dict[str, Any]]:
    """Execute a validated SELECT in a read-only transaction."""
    safe_query = validate_select_query(query)
    with closing(_connect()) as connection:
        connection.set_session(readonly=True, autocommit=False)
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(safe_query)
                return [_json_safe(dict(row)) for row in cursor.fetchall()]
