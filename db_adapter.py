from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any

try:
    import psycopg
except ImportError:
    psycopg = None

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'tai_san_manager.db'

def is_postgres() -> bool:
    url = os.getenv('DATABASE_URL', '').strip()
    return url.startswith(('postgresql://', 'postgres://'))

def convert_sql(sql: str) -> str:
    if not is_postgres():
        return sql
    sql = re.sub(r'INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT', 'SERIAL PRIMARY KEY', sql, flags=re.I)
    sql = sql.replace('INSERT OR IGNORE INTO', 'INSERT INTO')
    sql = sql.replace('?', '%s')
    # psycopg treats every % as placeholder prefix; escape LIKE literals such as '%Cầm cố%'.
    sql = re.sub(r'%(?!s|b|t)', '%%', sql)
    return sql

class CursorAdapter:
    def __init__(self, cur):
        self.cur = cur
        self.lastrowid = None

    def execute(self, sql: str, params: tuple | list = ()): 
        orig = sql
        sql = convert_sql(sql)
        if is_postgres() and orig.lstrip().upper().startswith('INSERT OR IGNORE INTO'):
            if 'users' in orig:
                sql += ' ON CONFLICT (username) DO NOTHING'
            elif 'bao_dam_records' in orig or 'giu_ho_records' in orig:
                sql += ' ON CONFLICT (so_ts_lcl) DO NOTHING'
        if is_postgres() and sql.lstrip().upper().startswith('INSERT INTO') and 'RETURNING id' not in sql and ('users' in sql or 'bao_dam_records' in sql or 'giu_ho_records' in sql):
            sql += ' RETURNING id'
            self.cur.execute(sql, params)
            row = self.cur.fetchone()
            self.lastrowid = row[0] if row else None
            return self
        self.cur.execute(sql, params)
        return self

    def fetchone(self):
        return self.cur.fetchone()

    def fetchall(self):
        return self.cur.fetchall()

class ConnAdapter:
    def __init__(self):
        self.conn = psycopg.connect(os.environ['DATABASE_URL'])

    def cursor(self):
        return CursorAdapter(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

def get_db():
    if is_postgres():
        if psycopg is None:
            raise RuntimeError('DATABASE_URL is PostgreSQL but psycopg is not installed')
        return ConnAdapter()
    return sqlite3.connect(str(DB_PATH))
