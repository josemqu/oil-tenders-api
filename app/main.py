from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .db import get_conn, init_pool, close_pool
from .schema import get_columns, get_primary_key, list_valid_columns

app = FastAPI(title="Oil Tenders API", version="0.1.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=config.CORS_ALLOW_CREDENTIALS,
    allow_methods=config.CORS_ALLOW_METHODS,
    allow_headers=config.CORS_ALLOW_HEADERS,
)

# Cached table metadata
_TABLE_COLUMNS: List[str] = []
_TABLE_PK: str = "id"
_TABLE_NAME: str = config.OFFERS_TABLE_NAME


@app.on_event("startup")
async def on_startup() -> None:
    global _TABLE_COLUMNS, _TABLE_PK
    await init_pool()
    _TABLE_COLUMNS, _TABLE_PK = await list_valid_columns(_TABLE_NAME)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await close_pool()


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "table": _TABLE_NAME}


@app.get("/offers/columns")
async def offers_columns() -> List[Dict[str, Any]]:
    return await get_columns(_TABLE_NAME)


@app.get("/offers/{item_id}")
async def get_offer(item_id: str) -> Dict[str, Any]:
    if _TABLE_PK not in _TABLE_COLUMNS:
        raise HTTPException(status_code=500, detail="Primary key not found in table columns")

    query = f"select * from public.{_TABLE_NAME} where \"{_TABLE_PK}\" = %s limit 1"
    async with get_conn() as aconn:
        rows = await aconn.execute(query, (item_id,))
        row = await rows.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        return row


@app.get("/offers")
async def list_offers(
    # Common filters (if the column exists)
    id: Optional[str] = None,
    company: Optional[str] = None,
    company_like: Optional[str] = None,
    product: Optional[str] = None,
    product_like: Optional[str] = None,
    volume_min: Optional[float] = Query(default=None, description="Min volume filter if 'volume' column exists"),
    volume_max: Optional[float] = Query(default=None, description="Max volume filter if 'volume' column exists"),
    # Generic patterns: eq_{col}, ilike_{col}, min_{col}, max_{col}
    eq: Optional[List[str]] = Query(default=None, description="List of 'col:value' pairs for exact matching"),
    ilike: Optional[List[str]] = Query(default=None, description="List of 'col:value' pairs for case-insensitive contains"),
    min: Optional[List[str]] = Query(default=None, description="List of 'col:value' numeric minimums"),
    max: Optional[List[str]] = Query(default=None, description="List of 'col:value' numeric maximums"),
    order_by: Optional[str] = Query(default=None, description="Column to order by (must be valid column)"),
    order_dir: Optional[str] = Query(default="desc", description="asc or desc"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    include_total: bool = Query(default=False, description="Include total count"),
) -> Dict[str, Any]:
    where_clauses: List[str] = []
    params: List[Any] = []

    def add_eq(col: str, value: Any) -> None:
        if col in _TABLE_COLUMNS:
            where_clauses.append(f'"{col}" = %s')
            params.append(value)

    def add_ilike(col: str, value: str) -> None:
        if col in _TABLE_COLUMNS:
            where_clauses.append(f'"{col}" ilike %s')
            params.append(f"%{value}%")

    def add_min(col: str, value: Any) -> None:
        if col in _TABLE_COLUMNS:
            where_clauses.append(f'"{col}" >= %s')
            params.append(value)

    def add_max(col: str, value: Any) -> None:
        if col in _TABLE_COLUMNS:
            where_clauses.append(f'"{col}" <= %s')
            params.append(value)

    # Convenience filters
    if id is not None and _TABLE_PK in _TABLE_COLUMNS:
        add_eq(_TABLE_PK, id)
    if company is not None:
        add_eq("company", company)
    if company_like is not None:
        add_ilike("company", company_like)
    if product is not None:
        add_eq("product", product)
    if product_like is not None:
        add_ilike("product", product_like)
    if volume_min is not None:
        add_min("volume", volume_min)
    if volume_max is not None:
        add_max("volume", volume_max)

    # Generic eq/ilike/min/max lists (e.g., ?eq=country:US&eq=port:NY)
    def parse_pairs(pairs: Optional[List[str]], handler) -> None:
        if not pairs:
            return
        for item in pairs:
            if ":" not in item:
                continue
            col, val = item.split(":", 1)
            col = col.strip()
            val = val.strip()
            if not col or not val:
                continue
            handler(col, val)

    parse_pairs(eq, add_eq)
    parse_pairs(ilike, add_ilike)
    parse_pairs(min, add_min)
    parse_pairs(max, add_max)

    where_sql = ""
    if where_clauses:
        where_sql = " where " + " and ".join(where_clauses)

    # Safe order by
    order_col = order_by if order_by in _TABLE_COLUMNS else _TABLE_PK if _TABLE_PK in _TABLE_COLUMNS else None
    order_dir_norm = "asc" if order_dir and order_dir.lower() == "asc" else "desc"
    order_sql = f' order by "{order_col}" {order_dir_norm}' if order_col else ""

    base_sql = f"select * from public.{_TABLE_NAME}"
    page_sql = f"{base_sql}{where_sql}{order_sql} limit %s offset %s"

    resp: Dict[str, Any] = {"items": [], "count": 0, "limit": limit, "offset": offset, "total": 0}

    async with get_conn() as aconn:
        # Fetch page
        rows = await aconn.execute(page_sql, (*params, limit, offset))
        async for r in rows:
            resp["items"].append(r)
        resp["count"] = len(resp["items"])  # page count

        # Always include total count of matching rows (ignores pagination)
        count_sql = f"select count(*) as total from public.{_TABLE_NAME}{where_sql}"
        total_rows = await aconn.execute(count_sql, tuple(params))
        one = await total_rows.fetchone()
        resp["total"] = one["total"] if isinstance(one, dict) else one[0]

    return resp


# Uvicorn entrypoint helper
# Run: uvicorn app.main:app --reload
