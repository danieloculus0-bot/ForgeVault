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


class BrowseFileRequest(BaseModel):
    title: str = "Choose a file for ForgeVault"
    initial_dir: str | None = None


class BrowsePathResponse(BaseModel):
    selected: bool
    path: str | None = None


@router.get("/capabilities")
def desktop_capabilities(request: Request) -> dict:
    return {
        "desktop_bridge_enabled": desktop_bridge_enabled(),
        "browse_folder": desktop_bridge_enabled(),
        "browse_file": desktop_bridge_enabled(),
    }


def normalize_initial_dir(initial_dir: str | None) -> str:
    if initial_dir:
        try:
            resolved = Path(initial_dir).expanduser().resolve()
            if resolved.is_file():
                return str(resolved.parent)
            if resolved.is_dir():
                return str(resolved)
        except Exception:
            pass
    return str(Path.home())


@router.post("/browse-folder", response_model=BrowsePathResponse)
def browse_folder(payload: BrowseFolderRequest, request: Request) -> BrowsePathResponse:
    assert_desktop_request(request)
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"folder browser is unavailable: {exc}") from exc

    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(title=payload.title, initialdir=normalize_initial_dir(payload.initial_dir))
        root.destroy()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"folder browser failed: {exc}") from exc

    if not selected:
        return BrowsePathResponse(selected=False, path=None)
    return BrowsePathResponse(selected=True, path=str(Path(selected).resolve()))


@router.post("/browse-file", response_model=BrowsePathResponse)
def browse_file(payload: BrowseFileRequest, request: Request) -> BrowsePathResponse:
    assert_desktop_request(request)
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"file browser is unavailable: {exc}") from exc

    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilename(title=payload.title, initialdir=normalize_initial_dir(payload.initial_dir))
        root.destroy()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"file browser failed: {exc}") from exc

    if not selected:
        return BrowsePathResponse(selected=False, path=None)
    return BrowsePathResponse(selected=True, path=str(Path(selected).resolve()))
