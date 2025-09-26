from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .db import get_conn
from . import config


async def get_columns(table: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return column metadata for a table in the public schema.

    Response contains: column_name, data_type, is_nullable, ordinal_position
    """
    tbl = table or config.OFFERS_TABLE_NAME
    query = """
        select
            c.column_name,
            c.data_type,
            c.is_nullable,
            c.ordinal_position
        from information_schema.columns c
        where c.table_schema = 'public' and c.table_name = %s
        order by c.ordinal_position
    """
    async with get_conn() as aconn:
        rows = await aconn.execute(query, (tbl,))
        result: List[Dict[str, Any]] = []
        async for r in rows:
            # r is a dict thanks to dict_row
            result.append(
                {
                    "column_name": r["column_name"],
                    "data_type": r["data_type"],
                    "is_nullable": (r["is_nullable"].upper() == "YES") if isinstance(r["is_nullable"], str) else bool(r["is_nullable"]),
                    "ordinal_position": r["ordinal_position"],
                }
            )
        return result


async def get_primary_key(table: Optional[str] = None) -> Optional[str]:
    tbl = table or config.OFFERS_TABLE_NAME
    query = """
        select a.attname as column_name
        from   pg_index i
        join   pg_attribute a on a.attrelid = i.indrelid and a.attnum = any(i.indkey)
        where  i.indrelid = %s::regclass
        and    i.indisprimary
    """
    async with get_conn() as aconn:
        rows = await aconn.execute(query, (f"public.{tbl}",))
        first = await rows.fetchone()
        if not first:
            return None
        # first is a dict
        return first.get("column_name")


async def list_valid_columns(table: Optional[str] = None) -> Tuple[List[str], str]:
    cols_meta = await get_columns(table)
    cols = [c["column_name"] for c in cols_meta]
    pk = await get_primary_key(table)
    return cols, pk or "id"
