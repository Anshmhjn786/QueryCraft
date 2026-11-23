"""Bulk-load customer shopping transactions into PostgreSQL."""

import argparse
import csv
import os
import re
from contextlib import closing
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

CSV_FILE_PATH = "customer_shopping_data.csv"
CSV_COLUMNS = (
    "invoice_no",
    "customer_id",
    "gender",
    "age",
    "category",
    "quantity",
    "price",
    "payment_method",
    "invoice_date",
    "shopping_mall",
)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS shopping_transactions (
    invoice_no TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    gender TEXT NOT NULL,
    age SMALLINT NOT NULL,
    category TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price NUMERIC(12, 2) NOT NULL,
    payment_method TEXT NOT NULL,
    invoice_date DATE NOT NULL,
    shopping_mall TEXT NOT NULL
)
"""

COPY_SQL = """
COPY shopping_transactions (
    invoice_no, customer_id, gender, age, category, quantity, price,
    payment_method, invoice_date, shopping_mall
) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)
"""


def _resolve_csv_path(file_path: str | Path) -> Path:
    path = Path(file_path).expanduser()
    if path.is_absolute():
        candidates = [path]
    else:
        candidates = [
            Path.cwd() / path,
            Path(__file__).parent / path,
            Path(__file__).parent.parent / path,
        ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"CSV file not found: {file_path}")


def _validate_csv_header(csv_path: Path) -> None:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        header = next(csv.reader(csv_file), None)
    if tuple(header or ()) != CSV_COLUMNS:
        expected = ", ".join(CSV_COLUMNS)
        raise ValueError(f"CSV header must contain these columns in order: {expected}")


def _connect() -> psycopg2.extensions.connection:
    required = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise ValueError(f"Missing database environment variables: {', '.join(missing)}")

    return psycopg2.connect(
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
    )


def seed_database(file_path: str | Path = CSV_FILE_PATH) -> int:
    """Create the destination table and stream the CSV into it with COPY."""
    csv_path = _resolve_csv_path(file_path)
    _validate_csv_header(csv_path)

    with closing(_connect()) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_TABLE_SQL)
                cursor.execute("SET LOCAL DateStyle TO 'ISO, MDY'")
                with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                    cursor.copy_expert(COPY_SQL, csv_file)

                match = re.fullmatch(r"COPY (\d+)", cursor.statusmessage or "")
                if match is None:
                    raise RuntimeError("PostgreSQL did not report the number of copied rows.")
                return int(match.group(1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        default=CSV_FILE_PATH,
        help=f"CSV source path (default: {CSV_FILE_PATH})",
    )
    args = parser.parse_args()
    inserted_rows = seed_database(args.csv)
    print(f"Successfully inserted {inserted_rows} rows into shopping_transactions.")


if __name__ == "__main__":
    main()
