"""Interactive SemantiQL command-line interface."""

from pprint import pprint

import psycopg2
from openai import APIError
from pydantic import ValidationError

from database import execute_query
from engine import QueryPlan, generate_sql


def print_plan(plan: QueryPlan) -> None:
    print(f"\nIntent: {plan.intent}")
    print(f"Classification applied: {'yes' if plan.classification_applied else 'no'}")
    print(f"Explanation: {plan.explanation}")
    print(f"\nGenerated SQL:\n{plan.sql_query}")


def main() -> None:
    print("SemantiQL — enter a question, or type 'exit' to quit.")
    while True:
        try:
            user_query = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if user_query.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break
        if not user_query:
            continue

        try:
            plan = generate_sql(user_query)
            print_plan(plan)
            records = execute_query(plan.sql_query)
            print("\nResults:")
            pprint(records, sort_dicts=False)
        except (APIError, ValidationError, ValueError, psycopg2.Error) as exc:
            print(f"\nUnable to process the query: {exc}")


if __name__ == "__main__":
    main()
