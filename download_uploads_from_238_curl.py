#!/usr/bin/env python3
import json, subprocess, urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
UPLOADS=ROOT/'uploads'; UPLOADS.mkdir(exist_ok=True)
COOKIE='/tmp/pdf238.cookie'
BASE='http://192.168.1.238:3511/uploads/'
files=[]
for p in ['/tmp/bao.json','/tmp/giu.json']:
    for r in json.load(open(p)):
        f=r.get('pdf_file')
        if f and f not in files: files.append(f)
print(f'total_files={len(files)}', flush=True)
ok=skip=err=0
for i,f in enumerate(files,1):
    out=UPLOADS/f
    if out.exists() and out.stat().st_size>0:
        try:
            if out.open('rb').read(5).startswith(b'%PDF'):
                skip+=1; continue
        except Exception: pass
    tmp=out.with_suffix(out.suffix+'.tmp')
    url=BASE+urllib.parse.quote(f)
    r=subprocess.run(['curl','-fsSL','--retry','2','--connect-timeout','5','--max-time','60','-b',COOKIE,url,'-o',str(tmp)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode!=0:
        err+=1; tmp.unlink(missing_ok=True); print(f'ERR {i}/{len(files)} curl {r.returncode} {f}: {r.stderr[:160]}', flush=True); continue
    try: head=tmp.open('rb').read(5)
    except Exception: head=b''
    if not head.startswith(b'%PDF'):
        err+=1; tmp.unlink(missing_ok=True); print(f'ERR {i}/{len(files)} not_pdf {f}', flush=True); continue
    tmp.replace(out); ok+=1
    if i%100==0: print(f'progress {i}/{len(files)} ok={ok} skip={skip} err={err}', flush=True)
print(f'done ok={ok} skip={skip} err={err}', flush=True)
