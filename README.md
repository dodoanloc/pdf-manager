# Quản lý PDF và hồ sơ tài sản bảo đảm

**Repo:** `pdf-manager`  
**Mục đích:** Đăng nhập, tải lên, lưu trữ, tìm kiếm và quản lý PDF; có quản trị user và kế hoạch migration PostgreSQL.

## Người dùng nên biết

- Đây là mã nguồn ứng dụng nội bộ; dữ liệu runtime, DB, upload và secret không thuộc source code cần commit.
- Thay đổi chức năng phải đi qua branch → Pull Request → CI → reviewer `ktnqagribanktx-lang` → merge.
- Production không deploy trực tiếp từ máy local. Xem [`ROLLBACK.md`](ROLLBACK.md).

## Công nghệ và luồng chính

Python webapp + templates/static + SQLite/PostgreSQL adapter.

```text
Người dùng → giao diện frontend → backend/API hoặc server → DB/tệp cấu hình
```

## Cấu trúc repo

```text
├── app.py
├── db_adapter.py
├── templates/
├── static/
├── uploads/
├── requirements.txt
├── docs/
├── .github/
└── ROLLBACK.md
```

### Thành phần chính

- `app.py`: thành phần cần biết khi sửa app.
- `db_adapter.py`: thành phần cần biết khi sửa app.
- `templates/`: thành phần cần biết khi sửa app.
- `static/`: thành phần cần biết khi sửa app.
- `uploads/`: thành phần cần biết khi sửa app.
- `requirements.txt`: thành phần cần biết khi sửa app.

## Chạy và triển khai

- **Service:** `pdf-manager.service`
- **Port ghi nhận:** `?`
- Kiểm tra service: `systemctl --user status pdf-manager.service`
- Không sửa trực tiếp DB production khi chưa backup.

## Kiểm tra trước Pull Request

```bash
# Python nếu repo có file .py
python -m py_compile <changed-python-files>

# Node nếu repo có package.json/server.js
node --check <changed-js-file>

# Test riêng của repo nếu có
pytest -q   # hoặc npm test
```

## Quyền và dữ liệu

- Không commit token, password, API key, session, DB production, upload hoặc PII.
- Giữ nguyên phân quyền hiện hữu khi sửa API/UI.
- Với thay đổi schema hoặc file lưu trữ: backup trước, cập nhật runbook, test rollback.
