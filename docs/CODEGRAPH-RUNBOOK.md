# CodeGraph Runbook — PDF Manager

## Phạm vi

- Repo: `/home/locdodoan/webapps/projects/pdf-manager`
- Service: `pdf-manager.service`
- Ports: `3511`
- Index: `/home/locdodoan/webapps/projects/pdf-manager/.codegraph`
- Ghi chú nghiệp vụ: PDF management utilities; public mirror .238:3511. Exact PDF handling; no format break without approval.

## Chỉ mục hiện tại

- Công cụ: CodeGraph `1.4.1`
- Stats: 8 files, 252 nodes, 613 edges, Python + JavaScript, ~940 KB
- Pending changes lúc index: `0 added, 0 modified, 0 removed`
- `.codegraph/` là dữ liệu sinh local, không commit.

Kiểm tra mới nhất:

```bash
cd /home/locdodoan/webapps/projects/pdf-manager
codegraph sync .
codegraph status . --json
```

## Quy trình trước khi sửa

1. Đọc `docs/CONTEXT.md` và `AGENTS.md`.
2. Đồng bộ graph:

```bash
cd /home/locdodoan/webapps/projects/pdf-manager
codegraph sync .
```

3. Khảo sát luồng cần sửa:

```bash
codegraph explore "login auth permission records import export"
codegraph explore "database api frontend validation"
```

4. Với symbol cụ thể:

```bash
codegraph node '<symbol>'
codegraph callers '<symbol>'
codegraph callees '<symbol>'
codegraph impact '<symbol>'
```

5. Chỉ sửa sau khi đã xác định UI → route/API → validation → database/export → service health.

## Quy trình sau khi sửa

```bash
cd /home/locdodoan/webapps/projects/pdf-manager
codegraph sync .
codegraph status . --json
systemctl --user is-active pdf-manager.service
```

Health check HTTP theo port:

```bash
curl -fsS --max-time 5 http://127.0.0.1:3511/ >/dev/null && echo 3511_OK || echo 3511_FAIL
```

Vẫn phải chạy test nghiệp vụ/manual check. Graph không thay thế backup, rollback, test phân quyền, hay kiểm tra file xuất PDF/DOCX.

## Prompt mẫu cho Hermes

```text
Trong repo này, dùng CodeGraph phân tích blast radius trước khi sửa chức năng import/export/bản ghi. Đọc docs/CONTEXT.md trước, rồi liệt kê file/symbol/rủi ro.
```

```text
Review thay đổi hiện tại bằng CodeGraph: caller, callee, impact, endpoint liên quan; sau đó chạy health check service.
```
