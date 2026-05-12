from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileTypeInfo:
    extension: str
    category: str
    label: str
    preview_strategy: str = "metadata"
    vault_relevant: bool = True


FILE_TYPES: dict[str, FileTypeInfo] = {}


def register(category: str, label: str, extensions: list[str], preview_strategy: str = "metadata") -> None:
    for ext in extensions:
        normalized = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
        FILE_TYPES[normalized] = FileTypeInfo(
            extension=normalized,
            category=category,
            label=label,
            preview_strategy=preview_strategy,
        )


register("solidworks", "SOLIDWORKS Part", ["sldprt"], "cad3d")
register("solidworks", "SOLIDWORKS Assembly", ["sldasm"], "cad3d")
register("solidworks", "SOLIDWORKS Drawing", ["slddrw"], "drawing")
register("solidworks", "SOLIDWORKS Template", ["prtdot", "asmdot", "drwdot"], "metadata")

register("autodesk_inventor", "Autodesk Inventor Part", ["ipt"], "cad3d")
register("autodesk_inventor", "Autodesk Inventor Assembly", ["iam"], "cad3d")
register("autodesk_inventor", "Autodesk Inventor Drawing", ["idw"], "drawing")
register("autodesk_inventor", "Autodesk Inventor Presentation", ["ipn"], "cad3d")

register("autodesk", "AutoCAD Drawing", ["dwg", "dwt", "dws"], "drawing")
register("autodesk", "DXF Drawing", ["dxf"], "drawing")
register("autodesk", "Fusion 360 Archive", ["f3d", "f3z"], "cad3d")
register("autodesk", "Autodesk Design Web Format", ["dwf", "dwfx"], "drawing")

register("neutral_cad", "STEP CAD", ["step", "stp"], "cad3d")
register("neutral_cad", "IGES CAD", ["iges", "igs"], "cad3d")
register("neutral_cad", "Parasolid CAD", ["x_t", "x_b", "xmt_txt", "xmt_bin"], "cad3d")
register("neutral_cad", "ACIS CAD", ["sat", "sab"], "cad3d")
register("neutral_cad", "JT CAD", ["jt"], "cad3d")
register("neutral_cad", "PRC CAD", ["prc"], "cad3d")
register("neutral_cad", "3DXML CAD", ["3dxml"], "cad3d")

register("catia", "CATIA File", ["catpart", "catproduct", "catdrawing", "cgr", "model", "exp", "session"], "cad3d")
register("creo_proe", "Creo/ProE File", ["prt", "asm", "drw", "neu", "xpr", "xas"], "cad3d")
register("nx_siemens", "Siemens NX File", ["prt", "fem", "sim"], "cad3d")
register("solid_edge", "Solid Edge File", ["par", "asm", "dft", "psm"], "cad3d")
register("onshape", "Onshape Export", ["onshape"], "metadata")

register("mesh_3d", "STL Mesh", ["stl"], "mesh3d")
register("mesh_3d", "OBJ Mesh", ["obj", "mtl"], "mesh3d")
register("mesh_3d", "3MF Package", ["3mf"], "mesh3d")
register("mesh_3d", "AMF Mesh", ["amf"], "mesh3d")
register("mesh_3d", "PLY Mesh", ["ply"], "mesh3d")
register("mesh_3d", "VRML/X3D", ["wrl", "vrml", "x3d"], "mesh3d")
register("mesh_3d", "Collada", ["dae"], "mesh3d")
register("mesh_3d", "glTF/GLB", ["gltf", "glb"], "mesh3d")
register("mesh_3d", "USD/USDZ", ["usd", "usda", "usdc", "usdz"], "mesh3d")
register("mesh_3d", "FBX", ["fbx"], "mesh3d")

register("cam_cnc", "G-code", ["gcode", "gco", "nc", "cnc", "tap", "eia", "min"], "text")
register("cam_cnc", "CAM Project", ["cam", "mcam", "mcamx", "sprut", "ncc", "hsm", "fmp"], "metadata")
register("cam_cnc", "Tool Library", ["tools", "tool", "hsmlib", "library"], "metadata")
register("cam_cnc", "Nest/Layout", ["nst", "nest", "lcc", "ord", "dnc"], "metadata")

register("additive", "Slicer Project/Profile", ["3mf", "amf", "gcode", "bgcode", "factory", "form", "lys", "ctb", "photon", "pwmo", "sl1", "sl1s"], "metadata")
register("additive", "Printer/Profile Config", ["ini", "json", "yaml", "yml", "cfg", "conf"], "text")

register("drawing_doc", "PDF", ["pdf"], "pdf")
register("drawing_doc", "Drawing/Image Document", ["tif", "tiff", "jpg", "jpeg", "png", "bmp", "gif", "webp", "heic", "svg"], "image")
register("drawing_doc", "Markup/Plot", ["plt", "hpgl", "cal", "cals"], "drawing")

register("office", "Excel", ["xls", "xlsx", "xlsm", "xlsb", "xltx", "xltm", "csv"], "spreadsheet")
register("office", "Word", ["doc", "docx", "docm", "dotx", "dotm", "rtf", "odt"], "document")
register("office", "PowerPoint", ["ppt", "pptx", "pptm", "ppsx", "odp"], "document")
register("office", "Text", ["txt", "md", "log", "xml", "html", "htm"], "text")

register("erp_quality", "Quality/Inspection Data", ["fai", "fair", "ppap", "cmm", "iqc", "oqc", "xlsx", "csv"], "metadata")
register("erp_quality", "Barcode/Label", ["btw", "lbl", "zpl", "epl", "prn"], "metadata")

register("archive", "Archive", ["zip", "7z", "rar", "tar", "gz", "tgz", "bz2", "xz", "cab"], "archive")
register("email", "Email", ["eml", "msg", "oft"], "document")

register("software_config", "Source/Script", ["py", "ps1", "bat", "cmd", "sh", "js", "ts", "cs", "cpp", "c", "h", "hpp", "java", "kt", "rs", "go"], "text")
register("software_config", "Config", ["json", "yaml", "yml", "toml", "ini", "cfg", "conf", "env", "properties"], "text")

# Files that should usually be skipped by bulk folder indexing.
IGNORED_SUFFIXES = {
    ".tmp", ".temp", ".bak", ".old", ".orig", ".swp", ".lock", ".lck", ".part", ".crdownload",
    ".ds_store", ".thumbs.db",
}

IGNORED_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", "node_modules", ".venv", "venv", "env", ".idea", ".vs", ".vscode",
}


def classify_file(path: str | Path) -> FileTypeInfo:
    suffix = Path(path).suffix.lower()
    if suffix in FILE_TYPES:
        return FILE_TYPES[suffix]
    return FileTypeInfo(extension=suffix or "", category="unknown", label="Unknown File Type", preview_strategy="metadata", vault_relevant=True)


def is_ignored_file(path: str | Path) -> bool:
    suffix = Path(path).suffix.lower()
    name = Path(path).name.lower()
    return suffix in IGNORED_SUFFIXES or name in {item.strip(".") for item in IGNORED_SUFFIXES}


def file_type_metadata(path: str | Path) -> dict:
    info = classify_file(path)
    return {
        "extension": info.extension,
        "category": info.category,
        "label": info.label,
        "preview_strategy": info.preview_strategy,
        "vault_relevant": info.vault_relevant,
        "known_type": info.category != "unknown",
    }
