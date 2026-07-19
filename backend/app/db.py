"""
Shared PostgreSQL connection helper.
Reads DATABASE_URL from .env (see README) — works with your port 5433 setup.
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/scs_db")


def get_connection():
    """Returns a new psycopg2 connection. Caller is responsible for closing it."""
    return psycopg2.connect(DB_URL)


def get_dict_cursor(conn):
    """Returns a cursor that yields rows as dicts instead of tuples."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
