from contextlib import asynccontextmanager
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .api.desktop import router as desktop_router
from .api.routes import router
from .config import settings
from .database import create_all


def frontend_asset_path(filename: str) -> Path:
    candidates = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root) / "frontend" / filename)
    candidates.extend(
        [
            Path.cwd() / "frontend" / filename,
            Path(__file__).resolve().parents[2] / "frontend" / filename,
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    searched = ", ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"ForgeVault frontend/{filename} not found. Searched: {searched}")


def frontend_index_path() -> Path:
    return frontend_asset_path("index.html")


def inject_optional_desktop_scripts(html: str) -> str:
    scripts = []
    for filename in ("onboarding-ui.js", "checkin-ui.js", "polish-ui.js"):
        try:
            scripts.append(frontend_asset_path(filename).read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue

    if not scripts:
        return html

    block = "\n".join(f"<script>\n{script}\n</script>" for script in scripts)
    if "</body>" in html:
        return html.replace("</body>", f"{block}\n</body>", 1)
    return f"{html}\n{block}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_schema:
        create_all()
    yield


app = FastAPI(title="ForgeVault API", version="0.1.0", lifespan=lifespan)
app.include_router(router, prefix="/api/v1")
app.include_router(desktop_router, prefix="/api/v1")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ui", response_class=HTMLResponse)
def web_ui() -> str:
    html = frontend_index_path().read_text(encoding="utf-8")
    return inject_optional_desktop_scripts(html)
