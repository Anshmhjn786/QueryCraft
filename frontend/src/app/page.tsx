"use client";

import { useState, type FormEvent } from "react";

type QueryResponse = {
  is_supported: boolean;
  classification: string;
  sql_query: string;
  explanation: string;
  data: Array<Record<string, unknown>>;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function displayValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function isQueryResponse(value: unknown): value is QueryResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.is_supported === "boolean" &&
    typeof candidate.classification === "string" &&
    typeof candidate.sql_query === "string" &&
    typeof candidate.explanation === "string" &&
    Array.isArray(candidate.data) &&
    candidate.data.every(
      (row) => typeof row === "object" && row !== null && !Array.isArray(row),
    )
  );
}

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submitQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt || loading) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(`${API_URL}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: trimmedPrompt }),
      });
      const body: unknown = await response.json();

      if (!response.ok) {
        const detail =
          typeof body === "object" &&
          body !== null &&
          "detail" in body &&
          typeof body.detail === "string"
            ? body.detail
            : "The query could not be completed.";
        throw new Error(detail);
      }

      if (!isQueryResponse(body)) {
        throw new Error("The API returned an invalid response.");
      }
      setResult(body);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not connect to the SemantiQL API.",
      );
    } finally {
      setLoading(false);
    }
  }

  const columns = result?.data.length ? Object.keys(result.data[0]) : [];

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-8 text-slate-100 sm:px-8 sm:py-12">
      <div className="mx-auto max-w-5xl">
        <header className="mb-12">
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-400/10 text-lg font-bold text-teal-300 ring-1 ring-teal-300/20">
              S
            </div>
            <span className="text-sm font-semibold tracking-wide text-slate-200">
              SemantiQL
            </span>
            <span className="rounded-full border border-slate-800 px-2.5 py-1 text-xs text-slate-400">
              TEXT TO SQL
            </span>
          </div>
          <p className="mb-3 text-sm font-medium text-teal-300">
            Business language, meet your data.
          </p>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
            Ask a question.
            <br />
            <span className="text-slate-400">Get an answer you can trust.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-slate-400">
            SemantiQL maps subjective terms to explicit business rules, then
            generates an explainable, read-only PostgreSQL query.
          </p>
        </header>

        <form
          onSubmit={submitQuery}
          className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3 shadow-2xl shadow-black/20 sm:flex sm:items-center sm:gap-3 sm:p-4"
        >
          <label className="sr-only" htmlFor="query-prompt">
            Ask your data a question
          </label>
          <input
            id="query-prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="e.g. Fetch customers who are good spenders"
            maxLength={4000}
            className="min-h-12 w-full bg-transparent px-3 text-base text-white outline-none placeholder:text-slate-500 sm:flex-1"
          />
          <button
            type="submit"
            disabled={loading || !prompt.trim()}
            className="mt-2 flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-teal-300 px-5 font-semibold text-slate-950 transition hover:bg-teal-200 disabled:cursor-not-allowed disabled:opacity-50 sm:mt-0 sm:w-auto"
          >
            {loading ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700/30 border-t-slate-800" />
                Classifying…
              </>
            ) : (
              "Ask SemantiQL"
            )}
          </button>
        </form>

        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span>Try:</span>
          {["good spenders", "frequent buyers", "inactive customers"].map(
            (example) => (
              <button
                key={example}
                type="button"
                onClick={() => setPrompt(`Show me ${example}`)}
                className="rounded-full border border-slate-800 px-3 py-1.5 transition hover:border-teal-400/50 hover:text-teal-200"
              >
                {example}
              </button>
            ),
          )}
        </div>

        <div aria-live="polite" className="mt-8">
          {loading && (
            <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/50 px-5 py-4 text-sm text-slate-300">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-teal-300/30 border-t-teal-300" />
              Classifying intent and querying PostgreSQL…
            </div>
          )}

          {error && (
            <div
              role="alert"
              className="rounded-xl border border-rose-400/20 bg-rose-400/5 px-5 py-4 text-sm text-rose-200"
            >
              {error}
            </div>
          )}

          {result && (
            <section className="space-y-5">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 sm:p-6">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-sm font-semibold text-white">
                    Intent classification
                  </h2>
                  <span
                    className={`rounded-full border px-3 py-1 text-xs font-medium ${
                      result.is_supported
                        ? "border-teal-300/20 bg-teal-300/10 text-teal-200"
                        : "border-amber-300/20 bg-amber-300/10 text-amber-200"
                    }`}
                  >
                    {result.is_supported ? result.classification : "Unsupported"}
                  </span>
                </div>
                <p className="text-sm leading-6 text-slate-300">
                  {result.explanation}
                </p>
              </div>

              {result.is_supported && result.sql_query && (
                <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
                  <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
                    <h2 className="text-sm font-semibold text-white">
                      Generated PostgreSQL
                    </h2>
                    <span className="text-xs text-slate-500">READ ONLY</span>
                  </div>
                  <pre className="overflow-x-auto p-5 text-sm leading-6">
                    <code className="font-mono text-teal-100">
                      {result.sql_query}
                    </code>
                  </pre>
                </div>
              )}

              {result.is_supported && (
                <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
                  <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
                    <h2 className="text-sm font-semibold text-white">
                      Query results
                    </h2>
                    <span className="text-xs text-slate-500">
                      {result.data.length}{" "}
                      {result.data.length === 1 ? "record" : "records"}
                    </span>
                  </div>
                  {columns.length ? (
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[480px] text-left text-sm">
                        <thead className="bg-slate-950/60 text-xs uppercase tracking-wider text-slate-500">
                          <tr>
                            {columns.map((column) => (
                              <th key={column} className="px-5 py-3 font-medium">
                                {column.replaceAll("_", " ")}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/80">
                          {result.data.map((record, rowIndex) => (
                            <tr
                              key={rowIndex}
                              className="transition hover:bg-slate-800/30"
                            >
                              {columns.map((column) => (
                                <td
                                  key={column}
                                  className="whitespace-nowrap px-5 py-3.5 text-slate-300"
                                >
                                  {displayValue(record[column])}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="px-5 py-8 text-center text-sm text-slate-500">
                      No matching records found.
                    </p>
                  )}
                </div>
              )}
            </section>
          )}
        </div>
        <footer className="mt-12 border-t border-slate-900 pt-5 text-xs text-slate-600">
          SemantiQL · Explicit business rules. Explainable SQL. Read-only data.
        </footer>
      </div>
    </main>
  );
}
