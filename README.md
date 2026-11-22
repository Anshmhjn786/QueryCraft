# ⚡ SemantiQL

> An intelligent, context-aware Text-to-SQL translation layer with an intent classification engine. Translates subjective business jargon into deterministic, read-only PostgreSQL queries.

---

## 📌 Overview

Standard Text-to-SQL tools fail when queries involve subjective business logic. When an analyst asks for *"customers who are good spenders,"* an LLM cannot guess what "good" means without hallucinating thresholds.

**SemantiQL** adds a dedicated **Classification & Business Rules Layer** on top of relational schemas. It categorizes user intent, translates qualitative business rules into explicit math/aggregations, and guarantees type-safe, read-only SQL generation via Pydantic structured outputs.

---

## 🏗️ Architecture
