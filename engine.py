"""LLM-backed intent classification and read-only SQL generation."""

import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

load_dotenv()

SYSTEM_PROMPT = """
You are SemantiQL, a PostgreSQL text-to-SQL assistant. Return exactly one JSON
object with these four fields:
- intent: a concise label for the user's request
- classification_applied: true when an explicit business rule was used, false otherwise
- sql_query: one read-only PostgreSQL SELECT statement
- explanation: a concise explanation of the interpretation and query

Database schema:
customers(customer_id INTEGER PRIMARY KEY, name TEXT, email TEXT)
orders(order_id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers,
       order_date DATE, total_amount NUMERIC)

Business metric rules:
- "good spender" and "high spender" mean SUM(orders.total_amount) > 1000.
- "frequent buyer" means COUNT(orders.order_id) >= 5.

When applying a customer metric, join customers to orders on customer_id, group
by the customer columns you select, and use HAVING for the aggregate threshold.
Use table aliases only when they remain clear. Never invent tables or columns.
Generate only SELECT statements; do not generate modifying statements, DDL, or
multiple SQL statements. If the request cannot be answered using this schema,
return a valid SELECT that returns no rows and explain the limitation.
"""


class QueryPlan(BaseModel):
    """Validated response from the text-to-SQL model."""

    model_config = ConfigDict(extra="forbid", strict=True)

    intent: str = Field(min_length=1)
    classification_applied: bool
    sql_query: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


def _client_and_model() -> tuple[OpenAI, str]:
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        base_url = "https://api.groq.com/openai/v1"
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        base_url = None
    else:
        raise ValueError("LLM_PROVIDER must be either 'groq' or 'openai'.")

    if not api_key:
        key_name = "GROQ_API_KEY" if provider == "groq" else "OPENAI_API_KEY"
        raise ValueError(f"{key_name} must be set to use the {provider} provider.")

    return OpenAI(api_key=api_key, base_url=base_url), model


def generate_sql(user_query: str) -> QueryPlan:
    """Classify a natural-language request and return its validated SQL plan."""
    normalized_query = user_query.strip()
    if not normalized_query:
        raise ValueError("The natural-language query cannot be empty.")

    client, model = _client_and_model()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": normalized_query},
        ],
        response_format={"type": "json_object"},
    )
    content: Optional[str] = response.choices[0].message.content
    if not content:
        raise ValueError("The LLM returned an empty response.")

    try:
        return QueryPlan.model_validate_json(content)
    except ValidationError as exc:
        raise ValueError("The LLM response did not match the required query-plan schema.") from exc
