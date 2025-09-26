import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env.local if present
# Search from project root where this file resides, and parent
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env.local"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    # Also allow environment variables to be provided by the runtime
    load_dotenv()


def env_str(key: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(key, default)
    return val


def env_int(key: str, default: Optional[int] = None) -> Optional[int]:
    v = os.getenv(key)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


SUPABASE_HOST = env_str("SUPABASE_HOST")
SUPABASE_PORT = env_int("SUPABASE_PORT", 5432) or 5432
SUPABASE_DB_NAME = env_str("SUPABASE_DB_NAME", "postgres") or "postgres"
SUPABASE_USER = env_str("SUPABASE_USER", "postgres") or "postgres"
SUPABASE_PASSWORD = env_str("SUPABASE_PASSWORD") or ""
SUPABASE_POOL_MODE = env_str("SUPABASE_POOL_MODE", "session") or "session"
OFFERS_TABLE_NAME = env_str("OFFERS_TABLE_NAME", "oil_offers_export") or "oil_offers_export"

# Optional app settings
APP_PORT = env_int("APP_PORT", 8000) or 8000
APP_HOST = env_str("APP_HOST", "0.0.0.0") or "0.0.0.0"
APP_DEBUG = env_str("APP_DEBUG", "false").lower() in ("1", "true", "yes", "on")

# Connection pool sizes
POOL_MIN_SIZE = env_int("DB_POOL_MIN", 1) or 1
POOL_MAX_SIZE = env_int("DB_POOL_MAX", 10) or 10


def build_conninfo() -> str:
    host = SUPABASE_HOST
    port = SUPABASE_PORT
    db = SUPABASE_DB_NAME
    user = SUPABASE_USER
    password = SUPABASE_PASSWORD
    # Enforce SSL for Supabase and readonly at session level later
    # Note: we don't embed read_only here because psycopg3 exposes a connection attribute
    return (
        f"host={host} port={port} dbname={db} user={user} password={password} "
        f"sslmode=require"
    )
