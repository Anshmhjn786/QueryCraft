"""PostgreSQL connection and guarded read-only query execution."""

import os
from contextlib import closing
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
import sqlparse
from sqlparse import tokens as sql_tokens

load_dotenv()

_BLOCKED_KEYWORDS = {
    "ALTER",
    "CREATE",
    "DELETE",
    "DROP",
    "GRANT",
    "INSERT",
    "MERGE",
    "REVOKE",
    "TRUNCATE",
    "UPDATE",
}


def _connect() -> psycopg2.extensions.connection:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)

    required = ("PGDATABASE", "PGUSER", "PGPASSWORD")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise ValueError(f"Missing database environment variables: {', '.join(missing)}")

    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    )


def validate_select_query(query: str) -> str:
    """Accept exactly one SELECT statement and reject modifying SQL tokens."""
    if not query or not query.strip():
        raise ValueError("SQL query cannot be empty.")

    statements = [statement for statement in sqlparse.parse(query) if str(statement).strip()]
    if len(statements) != 1 or statements[0].get_type() != "SELECT":
        raise ValueError("Only one SELECT statement is allowed.")

    def reject_modifying_tokens(token_list: Any) -> None:
        for token in token_list.tokens:
            if token.ttype in (sql_tokens.Keyword.DML, sql_tokens.Keyword.DDL):
                if token.normalized.upper() in _BLOCKED_KEYWORDS:
                    raise ValueError(
                        f"SQL contains a prohibited {token.normalized.upper()} operation."
                    )
            if token.is_group:
                reject_modifying_tokens(token)

    reject_modifying_tokens(statements[0])
    return query.strip()


def execute_query(query: str) -> list[dict[str, Any]]:
    """Validate and execute a SELECT statement, returning rows as dictionaries."""
    safe_query = validate_select_query(query)
    with closing(_connect()) as connection:
        connection.set_session(readonly=True, autocommit=False)
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(safe_query)
                return [dict(row) for row in cursor.fetchall()]
