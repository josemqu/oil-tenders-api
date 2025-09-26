from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from . import config

_pool: Optional[AsyncConnectionPool] = None


async def init_pool() -> None:
    global _pool
    if _pool is not None:
        return

    conninfo = config.build_conninfo()
    _pool = AsyncConnectionPool(
        conninfo,
        min_size=config.POOL_MIN_SIZE,
        max_size=config.POOL_MAX_SIZE,
        kwargs={
            "autocommit": True,
            "prepare_threshold": None,  # disable prepared statements to be proxy-friendly
        },
    )

    # Warm up one connection and set session defaults
    async with _pool.connection() as aconn:
        aconn.row_factory = dict_row
        # Ensure SSL is used (handled by conninfo sslmode=require)
        # Enforce read-only session
        await aconn.execute("set session characteristics as transaction read only")
        # Optional: set statement timeout (ms)
        await aconn.execute("set statement_timeout = 15000")


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_conn() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    if _pool is None:
        await init_pool()
    assert _pool is not None

    async with _pool.connection() as aconn:
        aconn.row_factory = dict_row
        # ensure readonly at connection level too
        try:
            aconn.read_only = True  # psycopg3 connection level flag
        except Exception:
            # fallback to SQL command
            await aconn.execute("set session characteristics as transaction read only")
        yield aconn
