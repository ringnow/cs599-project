"""GET /api/download/{filename} — File download endpoint."""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

OUTPUT_DIR = Path.home() / ".cs599-agent" / "output"


@router.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download a generated file (docx/pdf)."""
    # Sanitize: prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/octet-stream",
    )