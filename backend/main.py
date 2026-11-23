"""FastAPI application for the SemantiQL query API."""

import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from database import (
    DatabaseConfigurationError,
    UnsafeQueryError,
    execute_query,
)
from engine import QueryEngineError, QueryEngineResponse, generate_query

app = FastAPI(title="SemantiQL API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


class QueryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    prompt: str = Field(min_length=1, max_length=4000)


class QueryAPIResponse(QueryEngineResponse):
    data: list[dict[str, object]]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/query", response_model=QueryAPIResponse)
def query_endpoint(request: QueryRequest) -> QueryAPIResponse:
    try:
        plan = generate_query(request.prompt)
    except QueryEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not plan.is_supported:
        if plan.sql_query:
            raise HTTPException(
                status_code=502,
                detail="Unsupported query plans must not contain SQL.",
            )
        return QueryAPIResponse(**plan.model_dump(), data=[])

    try:
        records = execute_query(plan.sql_query)
    except UnsafeQueryError as exc:
        raise HTTPException(status_code=502, detail="The generated SQL was rejected.") from exc
    except DatabaseConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except psycopg2.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="The database query failed. Check the database setup and schema.",
        ) from exc

    return QueryAPIResponse(**plan.model_dump(), data=records)
