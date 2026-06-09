"""POST /api/export — Export report to Word / PDF."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from src.skills.registry import get_skill_registry
from src.skills.base import SkillContext

router = APIRouter()


class ExportRequest(BaseModel):
    content: str
    title: str = "Research Report"
    format: str = "docx"          # "docx" | "pdf"
    author: str = ""
    language: str = "en"          # "en" | "zh"


@router.post("/api/export")
async def export_document(req: ExportRequest):
    """Export markdown content as Word or PDF."""
    ctx = SkillContext(
        topic=req.title,
        custom_params={
            "content": req.content,
            "format": req.format,
            "title": req.title,
            "author": req.author or "CS599 Research Assistant",
            "language": req.language or "en",
        },
    )
    sr = get_skill_registry().execute("office_export", ctx)
    if sr.success:
        return {
            "url": sr.content,
            "filename": sr.metadata.get("filename", ""),
            "size": sr.metadata.get("size", 0),
        }
    return {"error": sr.error}, 400