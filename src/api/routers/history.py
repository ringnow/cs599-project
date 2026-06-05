"""GET/DELETE /api/history — Report history management."""
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from pathlib import Path

router = APIRouter()

REPORT_DIR = Path.home() / ".cs599-agent" / "reports"
REPORT_INDEX = REPORT_DIR / "index.json"


class HistoryItem(BaseModel):
    id: str
    mode: str
    topic: str
    display_name: str
    time: str
    has_sources: bool = False


class HistoryContent(BaseModel):
    id: str
    content: str


def _load_reports() -> list:
    if REPORT_INDEX.exists():
        try:
            return json.loads(REPORT_INDEX.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _load_report_content(report: dict) -> str:
    """Read the markdown content for a report entry."""
    filepath = REPORT_DIR / report.get("filename", "")
    if filepath.exists():
        try:
            return filepath.read_text(encoding="utf-8")
        except Exception:
            return ""
    return ""


def save_report(mode: str, topic: str, content: str, display_name: str = "") -> str:
    """Save a generated report to disk so it persists across restarts.

    Returns the report id.
    """
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_id = str(uuid.uuid4())[:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    filename = f"{report_id}.md"
    (REPORT_DIR / filename).write_text(content, encoding="utf-8")
    reports = _load_reports()
    reports.insert(0, {
        "id": report_id,
        "mode": mode,
        "topic": topic,
        "display_name": display_name or topic,
        "time": now,
        "filename": filename,
        "has_sources": False,
    })
    REPORT_INDEX.write_text(
        json.dumps(reports[:100], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report_id


@router.get("/history")
async def list_history():
    """返回历史列表，直接包含全文内容，前端无需逐条加载。"""
    reports = _load_reports()[:50]
    result = []
    for r in reports:
        result.append({
            "id": r.get("id", ""),
            "mode": r.get("mode", ""),
            "topic": r.get("topic", ""),
            "display_name": r.get("display_name", r.get("topic", "未命名任务")),
            "time": r.get("time", ""),
            "has_sources": r.get("has_sources", False),
            "content": _load_report_content(r),
        })
    return result


@router.get("/history/{report_id}", response_model=HistoryContent)
async def get_history(report_id: str):
    reports = _load_reports()
    for r in reports:
        if r["id"] == report_id:
            filepath = REPORT_DIR / r["filename"]
            if filepath.exists():
                return HistoryContent(id=report_id, content=filepath.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="Report not found")


@router.delete("/history/{report_id}")
async def delete_history(report_id: str):
    reports = _load_reports()
    for r in reports:
        if r["id"] == report_id:
            filepath = REPORT_DIR / r["filename"]
            if filepath.exists():
                filepath.unlink()
            reports = [x for x in reports if x["id"] != report_id]
            REPORT_INDEX.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
            return {"status": "ok", "message": "已删除"}
    raise HTTPException(status_code=404, detail="Report not found")