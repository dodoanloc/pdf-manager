# PDF Manager PostgreSQL Migration

Ngày chuyển: 2026-05-05

## Trạng thái

Đã migrate dữ liệu từ SQLite `tai_san_manager.db` sang PostgreSQL `pdf_manager`.

- Role: `pdf_app`
- Database: `pdf_manager`
- Dữ liệu đã migrate:
  - users: 7
  - bao_dam_records: 2027
  - giu_ho_records: 5676

## Ghi chú vận hành

Service hiện chạy qua systemd system service:

- `/etc/systemd/system/qsd-flask.service`
- port `3511`

## Kiểm tra nhanh

```bash
export DATABASE_URL='postgresql://pdf_app:<password>@localhost:5432/pdf_manager'
psql "$DATABASE_URL" -Atqc "select 'users', count(*) from users union all select 'bao_dam_records', count(*) from bao_dam_records union all select 'giu_ho_records', count(*) from giu_ho_records;"
```
