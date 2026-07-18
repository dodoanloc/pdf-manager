#!/usr/bin/env python3
import json
import os
import time
import shutil
import pathlib
import urllib.parse
import urllib.request
import http.cookiejar

ROOT = pathlib.Path('/home/locdodoan/webapps/projects/pdf-manager')
UPLOADS = ROOT / 'uploads'
MIRROR = 'http://192.168.1.238:3511'
TS = time.strftime('%Y%m%d-%H%M%S')
BACKUP = ROOT / 'backups' / f'bad-pdf-bulk-restore-{TS}'
BACKUP.mkdir(parents=True, exist_ok=True)
MANIFEST = BACKUP / 'manifest.jsonl'

bad = []
for p in sorted(UPLOADS.glob('*.pdf')):
    try:
        head = p.read_bytes()[:8]
    except Exception as exc:
        bad.append((p, f'read_error:{exc}'))
        continue
    if not head.startswith(b'%PDF'):
        bad.append((p, head.hex()))

print(f'bad_count={len(bad)}')

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
req = urllib.request.Request(
    MIRROR + '/api/login',
    data=json.dumps({'username': 'admin', 'password': 'admin'}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
opener.open(req, timeout=20).read()

restored = 0
failed = 0
skipped = 0
with MANIFEST.open('a', encoding='utf-8') as mf:
    for i, (p, reason) in enumerate(bad, 1):
        name = p.name
        rec = {'file': name, 'old_size': p.stat().st_size if p.exists() else None, 'old_head': reason}
        try:
            url = MIRROR + '/uploads/' + urllib.parse.quote(name)
            data = opener.open(url, timeout=60).read()
            if not data.startswith(b'%PDF'):
                rec.update(status='skipped_mirror_not_pdf', mirror_size=len(data), mirror_head=data[:16].hex())
                skipped += 1
            else:
                shutil.copy2(p, BACKUP / name)
                tmp = p.with_suffix(p.suffix + '.restore-tmp')
                tmp.write_bytes(data)
                os.replace(tmp, p)
                rec.update(status='restored', new_size=len(data), new_head=data[:8].decode('latin1'))
                restored += 1
        except Exception as exc:
            rec.update(status='failed', error=repr(exc))
            failed += 1
        mf.write(json.dumps(rec, ensure_ascii=False) + '\n')
        mf.flush()
        if i % 100 == 0:
            print(f'progress={i}/{len(bad)} restored={restored} skipped={skipped} failed={failed}', flush=True)

print(f'DONE restored={restored} skipped={skipped} failed={failed} backup={BACKUP} manifest={MANIFEST}')
