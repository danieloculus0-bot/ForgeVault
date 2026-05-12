import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


router = APIRouter(prefix="/desktop", tags=["desktop"])


TRUE_VALUES = {"1", "true", "yes", "on"}


def desktop_bridge_enabled() -> bool:
    return os.environ.get("FORGEVAULT_ENABLE_DESKTOP_BRIDGE", "false").strip().lower() in TRUE_VALUES


def assert_desktop_request(request: Request) -> None:
    if not desktop_bridge_enabled():
        raise HTTPException(status_code=404, detail="desktop bridge is not enabled")
    host = request.client.host if request.client else ""
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise HTTPException(status_code=403, detail="desktop bridge only accepts local requests")


class BrowseFolderRequest(BaseModel):
    title: str = "Choose a source folder for ForgeVault"
    initial_dir: str | None = None


class BrowseFolderResponse(BaseModel):
    selected: bool
    path: str | None = None


@router.get("/capabilities")
def desktop_capabilities(request: Request) -> dict:
    return {
        "desktop_bridge_enabled": desktop_bridge_enabled(),
        "browse_folder": desktop_bridge_enabled(),
    }


@router.post("/browse-folder", response_model=BrowseFolderResponse)
def browse_folder(payload: BrowseFolderRequest, request: Request) -> BrowseFolderResponse:
    assert_desktop_request(request)
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"folder browser is unavailable: {exc}") from exc

    initial_dir = payload.initial_dir
    if initial_dir:
        try:
            initial_dir = str(Path(initial_dir).expanduser().resolve())
        except Exception:
            initial_dir = None

    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(title=payload.title, initialdir=initial_dir or str(Path.home()))
        root.destroy()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"folder browser failed: {exc}") from exc

    if not selected:
        return BrowseFolderResponse(selected=False, path=None)
    return BrowseFolderResponse(selected=True, path=str(Path(selected).resolve()))
