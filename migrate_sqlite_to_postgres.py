#!/usr/bin/env python3
from __future__ import annotations
import os, sqlite3, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from app import init_db
from db_adapter import get_db

TABLES={
 'users':['id','username','password_hash','full_name','role','unit_code','can_upload','can_delete','can_view_all','created_at'],
 'bao_dam_records':['id','ma_kh','ten_kh','so_ts_lcl','ngay_nhap','serial','vi_tri','don_vi','pdf_file','pdf_upload_date','created_at'],
 'giu_ho_records':['id','ma_kh','ten_kh','so_ts_lcl','ngay_nhap','serial','vi_tri','don_vi','pdf_file','pdf_upload_date','created_at'],
}

def rows(table, cols):
    conn=sqlite3.connect(ROOT/'tai_san_manager.db'); conn.row_factory=sqlite3.Row
    try:
        have={r[1] for r in conn.execute(f'pragma table_info({table})')}
        sel=[c for c in cols if c in have]
        return [{c:(r[c] if c in sel else None) for c in cols} for r in conn.execute(f"select {', '.join(sel)} from {table}")]
    finally: conn.close()

def main():
    if not os.getenv('DATABASE_URL','').startswith(('postgresql://','postgres://')):
        print('DATABASE_URL must be postgres', file=sys.stderr); return 2
    init_db()
    conn=get_db(); cur=conn.cursor()
    for table, cols in TABLES.items():
        data=rows(table, cols)
        ph=', '.join(['%s']*len(cols)); colsql=', '.join(cols)
        conflict='id' if table=='users' else 'id'
        updates=', '.join([f'{c}=excluded.{c}' for c in cols if c!='id'])
        sql=f"insert into {table} ({colsql}) values ({ph}) on conflict ({conflict}) do update set {updates}"
        for r in data: cur.execute(sql, tuple(r[c] for c in cols))
        print(f'{table}: {len(data)}')
    for table in TABLES:
        cur.execute(f"select setval(pg_get_serial_sequence('{table}','id'), coalesce(max(id),1)) from {table}")
    conn.commit(); conn.close()
    return 0
if __name__=='__main__': raise SystemExit(main())
