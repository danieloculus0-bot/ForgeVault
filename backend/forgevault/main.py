from contextlib import asynccontextmanager
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .api.desktop import router as desktop_router
from .api.routes import router
from .config import settings
from .database import create_all


def frontend_index_path() -> Path:
    candidates = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root) / "frontend" / "index.html")
    candidates.extend(
        [
            Path.cwd() / "frontend" / "index.html",
            Path(__file__).resolve().parents[2] / "frontend" / "index.html",
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    searched = ", ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"ForgeVault frontend/index.html not found. Searched: {searched}")


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
    return frontend_index_path().read_text(encoding="utf-8")
