# SemantiQL

SemantiQL maps subjective business terms to explicit PostgreSQL rules before
generating and running a read-only query. The repository includes a FastAPI
backend and a Next.js App Router frontend.

## Business rules

- **Good spender:** `SUM(orders.total_amount) > 1000`
- **Frequent buyer:** `COUNT(orders.id) >= 5`
- **Inactive:** no matching orders

The backend schema uses `orders.id` as the order identifier; this is the `order_id`
referred to in the frequent-buyer rule.

## Requirements

- Python 3.10+
- Node.js 20.9+
- PostgreSQL
- A Groq API key

## Setup

### 1. Prepare PostgreSQL

Create a database named `semantiql` (or choose another name and update the
backend environment file), then run the schema and sample data script:

```powershell
psql -U postgres -d semantiql -f backend/schema.sql
```

### 2. Start the backend

```powershell
cd backend
Copy-Item .env.example .env
# Set GROQ_API_KEY and the DB_* values in .env
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs at `http://localhost:8000`; its interactive API docs are available
at `http://localhost:8000/docs`.

To bulk-load `customer_shopping_data.csv` into `shopping_transactions`, after
configuring `backend/.env`, run from the repository root:

```powershell
python backend/seed_db.py
```

Provide a different CSV path with `python backend/seed_db.py --csv path\to\data.csv`.
The default path is resolved from the current directory or repository root.

### 3. Start the frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. To use a non-default API URL, set
`NEXT_PUBLIC_API_URL` before starting Next.js.

## API

`POST /api/query`

```json
{
  "prompt": "Fetch customers who are good spenders"
}
```

The response includes `is_supported`, `classification`, `sql_query`,
`explanation`, and `data`. Unsupported requests return an empty `data` array
without executing SQL. Generated statements are constrained to one `SELECT`
and run in a PostgreSQL read-only transaction.
