"""
Unit tests for Database Provider and Concurrency (WAL Mode)
===========================================================
"""

import pytest
import sqlite3
import os
import sys
import concurrent.futures

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from utils.shared import get_db_connection, DB_PATH
from db_data_provider import DatabaseDataProvider


def test_sqlite_wal_pragmas():
    conn = get_db_connection(DB_PATH, readonly=False)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0].lower()
    assert mode in ['wal', 'memory'], f"Expected WAL mode, got {mode}"
    
    cursor.execute("PRAGMA busy_timeout;")
    timeout = cursor.fetchone()[0]
    assert timeout >= 5000, f"Expected busy_timeout >= 5000, got {timeout}"
    
    conn.close()


def test_concurrent_read_queries():
    def fetch_league(code):
        provider = DatabaseDataProvider()
        df = provider.get_smart_data(code, temporadas=1, enrich=False)
        return len(df) if df is not None else 0

    leagues = ['E0', 'SP1', 'D1', 'I1', 'F1', 'P1', 'N1', 'ARG']
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(fetch_league, leagues))
    
    assert all(r > 0 for r in results), f"Some leagues returned 0 rows: {results}"
