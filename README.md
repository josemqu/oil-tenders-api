# Oil Tenders API (FastAPI)

FastAPI service exposing a read-only REST API over your Supabase Postgres database. It connects using credentials from `.env.local` and only performs SELECT queries (read-only session enforced).

## Features
- Read-only connection to Supabase Postgres with SSL.
- Health check: `GET /health`.
- Offers table endpoints (table configurable via `OFFERS_TABLE_NAME`):
  - `GET /offers` list with dynamic filters, pagination, ordering.
  - `GET /offers/{id}` fetch by primary key.
  - `GET /offers/columns` schema metadata for the table.
- Flexible filters via query params:
  - Convenience: `company`, `company_like`, `product`, `product_like`, `volume_min`, `volume_max`, and `id` (primary key).
  - Generic: `eq=col:value`, `ilike=col:value`, `min=col:value`, `max=col:value` (can repeat multiple times).

## Requirements
- Python 3.10+

## Setup
1. Create and fill environment file from template:
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your Supabase host/user/password and table name
   ```

2. Install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Run the API:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. Open the docs:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Usage examples
- List offers (default 50 items):
  ```
  GET /offers
  ```
- Paginate and include total:
  ```
  GET /offers?limit=20&offset=40&include_total=true
  ```
- Order by a valid column ascending:
  ```
  GET /offers?order_by=created_at&order_dir=asc
  ```
- Filter by company (exact) and product (contains):
  ```
  GET /offers?company=ACME&product_like=diesel
  ```
- Generic filters (repeatable):
  ```
  GET /offers?eq=country:US&eq=port:NY&ilike=grade:jet&min=volume:1000&max=volume:5000
  ```
- Fetch by primary key value:
  ```
  GET /offers/{id}
  ```
- Inspect available columns:
  ```
  GET /offers/columns
  ```

## Notes
- The service enforces read-only transactions and sets a 15s statement timeout.
- The primary key is auto-detected; if not found, it defaults to `id`.
- If your table/columns differ, update `OFFERS_TABLE_NAME` or use the generic filter params.
