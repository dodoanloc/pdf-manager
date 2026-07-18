# Runbook — PDF Manager

## Đường dẫn
```bash
cd /home/locdodoan/.openclaw/workspace/pdf-manager
```

## Kiểm tra nhanh
```bash
git status
python3 --version
```

## Chạy thủ công
```bash
python3 server.py
```

## Service
```bash
systemctl --user status pdf-manager --no-pager
systemctl --user restart pdf-manager
journalctl --user -u pdf-manager -n 100 --no-pager
```

## Health check
```bash
curl -I http://127.0.0.1:CHUA_DANG_KY || true
```

## Backup nhanh
```bash
/home/locdodoan/webapps/scripts/backup-webapps.sh pdf-manager
```
