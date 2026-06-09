"""POST /api/export — 导出报告为 Word/PDF，支持模板和文档编辑。"""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

from src.skills.registry import get_skill_registry
from src.skills.base import SkillContext

router = APIRouter()
OUTPUT_DIR = Path.home() / ".cs599-agent" / "exports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ExportRequest(BaseModel):
    content: str
    format: str = "docx"
    filename: str = "report"
    template_path: str = ""


class EditRequest(BaseModel):
    content: str
    docx_path: str
    filename: str = "edited_report"


@router.post("/api/export")
async def export_report(req: ExportRequest):
    """Export Markdown content to DOCX or PDF."""
    try:
        ctx = SkillContext(
            topic="export",
            custom_params={
                "content": req.content,
                "format": req.format,
                "filename": req.filename,
                "template_path": req.template_path,
            }
        )
        sr = get_skill_registry().execute("word_export", ctx)
        if sr.success:
            return {
                "status": "ok",
                "file_path": sr.metadata.get("file_path", ""),
                "file_name": sr.metadata.get("file_name", ""),
                "size_bytes": sr.metadata.get("size_bytes", 0),
                "steps": sr.steps,
            }
        return {"status": "error", "message": sr.error}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/export/edit")
async def edit_document(req: EditRequest):
    """Append new content to an existing DOCX file."""
    try:
        if not Path(req.docx_path).exists():
            raise HTTPException(status_code=404, detail="文档文件不存在")

        ctx = SkillContext(
            topic="edit",
            custom_params={
                "content": req.content,
                "format": "docx",
                "filename": req.filename,
                "edit_mode": True,
                "edit_docx_path": req.docx_path,
            }
        )
        sr = get_skill_registry().execute("word_export", ctx)
        if sr.success:
            return {
                "status": "ok",
                "file_path": sr.metadata.get("file_path", ""),
                "file_name": sr.metadata.get("file_name", ""),
                "size_bytes": sr.metadata.get("size_bytes", 0),
            }
        return {"status": "error", "message": sr.error}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/export/upload-template")
async def upload_template(file: UploadFile = File(...)):
    """Upload a .docx template file for style cloning."""
    if not file.filename or not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="请上传 .docx 文件")

    dest = OUTPUT_DIR / "templates"
    dest.mkdir(parents=True, exist_ok=True)
    filepath = dest / file.filename

    content = await file.read()
    filepath.write_bytes(content)

    return {
        "status": "ok",
        "template_path": str(filepath),
        "file_name": file.filename,
        "size_bytes": len(content),
    }


@router.get("/api/export/templates")
async def list_templates():
    """List uploaded template files."""
    template_dir = OUTPUT_DIR / "templates"
    if not template_dir.exists():
        return {"templates": []}
    files = []
    for f in template_dir.iterdir():
        if f.suffix == ".docx":
            files.append({
                "name": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size,
            })
    return {"templates": files}


@router.get("/api/export/files")
async def list_exports():
    """List all exported files."""
    if not OUTPUT_DIR.exists():
        return {"files": []}
    files = []
    for f in sorted(OUTPUT_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix in (".docx", ".pdf"):
            files.append({
                "name": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size,
                "format": f.suffix[1:],
                "modified": f.stat().st_mtime,
            })
    return {"files": files}