#!/usr/bin/env python3
import json, urllib.request, urllib.parse, http.cookiejar
from pathlib import Path

BASE='http://192.168.1.238:3511/uploads/'
ROOT=Path(__file__).resolve().parent
UPLOADS=ROOT/'uploads'
COOKIE_FILE=Path('/tmp/pdf238.cookie')
UPLOADS.mkdir(exist_ok=True)

jar=http.cookiejar.MozillaCookieJar(str(COOKIE_FILE))
if COOKIE_FILE.exists():
    jar.load(ignore_discard=True, ignore_expires=True)
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

files=[]
for p in ['/tmp/bao.json','/tmp/giu.json']:
    data=json.load(open(p))
    for r in data:
        f=r.get('pdf_file')
        if f and f not in files:
            files.append(f)
print(f'total_files={len(files)}')
ok=skip=err=0
for i,f in enumerate(files,1):
    out=UPLOADS/f
    if out.exists() and out.stat().st_size>0:
        try:
            if out.open('rb').read(5).startswith(b'%PDF'):
                skip+=1
                continue
        except Exception:
            pass
    url=BASE+urllib.parse.quote(f)
    try:
        with opener.open(url, timeout=30) as resp:
            status=getattr(resp,'status',200)
            ctype=resp.headers.get('Content-Type','')
            tmp=out.with_suffix(out.suffix+'.tmp')
            with open(tmp,'wb') as w:
                while True:
                    b=resp.read(1024*512)
                    if not b: break
                    w.write(b)
            head=tmp.open('rb').read(5)
            if status!=200 or not head.startswith(b'%PDF'):
                err+=1
                tmp.unlink(missing_ok=True)
                print(f'ERR {i}/{len(files)} status={status} ctype={ctype} not_pdf {f}', flush=True)
                continue
            tmp.replace(out)
            ok+=1
    except Exception as e:
        err+=1
        print(f'ERR {i}/{len(files)} {f}: {e}', flush=True)
    if i%100==0:
        print(f'progress {i}/{len(files)} ok={ok} skip={skip} err={err}', flush=True)
print(f'done ok={ok} skip={skip} err={err}')
