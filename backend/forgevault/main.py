from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .api.routes import router
from .config import settings
from .database import create_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_schema:
        create_all()
    yield


app = FastAPI(title="ForgeVault API", version="0.1.0", lifespan=lifespan)
app.include_router(router, prefix="/api/v1")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ui", response_class=HTMLResponse)
def web_ui() -> str:
    return Path("frontend/index.html").read_text()
