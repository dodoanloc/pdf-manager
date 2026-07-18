# Context — PDF Manager

## Mục tiêu
PDF management utilities.

## Người dùng
- Cán bộ nội bộ.
- Ưu tiên thao tác nhanh, giao diện rõ, ít phải nhớ kỹ thuật.

## Thông tin kỹ thuật
- Đường dẫn: `/home/locdodoan/.openclaw/workspace/pdf-manager`
- Port: `CHUA_DANG_KY`
- Service: `pdf-manager`
- Stack: Python/web PDF utilities

## Luồng chính
- Đăng nhập/nhập dữ liệu nếu có.
- Kiểm tra dữ liệu.
- Xuất/in/tải file nếu có.
- Lưu lịch sử nếu nghiệp vụ yêu cầu.

## Quyết định thiết kế
- UI card-based, bo góc lớn, shadow rõ.
- Gradient cyan → indigo.
- Plus Jakarta Sans cho giao diện; Times New Roman cho biểu mẫu hành chính nếu cần.
- Desktop ưu tiên 2 cột; mobile 1 cột.

## Lưu ý nghiệp vụ
PDF management utilities.

## Không được làm
- Không phá format mẫu biểu khi chưa hỏi Sếp Lộc.
- Không xoá DB/upload/backups nếu chưa có backup mới.
- Không đổi port/service/domain mà không cập nhật registry.
