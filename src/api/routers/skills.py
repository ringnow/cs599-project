"""CRUD /api/skills — Skill management."""
import json
import tempfile
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional

from src.skills.registry import get_skill_registry

router = APIRouter()


class SkillResponse(BaseModel):
    name: str
    display_name: str
    description: str
    tags: List[str] = []
    version: str = ""
    is_user_skill: bool = False


class InstallCodeRequest(BaseModel):
    code: str
    filename: str = "custom_skill.py"


@router.get("/skills", response_model=List[SkillResponse])
async def list_skills():
    registry = get_skill_registry()
    skills = registry.list_skills()
    return [
        SkillResponse(
            name=s["name"],
            display_name=s.get("display_name", s["name"]),
            description=s.get("description", ""),
            tags=s.get("tags", []),
            version=s.get("version", ""),
            is_user_skill=registry.get_skill_source(s["name"]) == "user",
        )
        for s in skills
    ]


@router.post("/skills/install")
async def install_skill_code(req: InstallCodeRequest):
    registry = get_skill_registry()
    try:
        ok, msg = registry.install_from_code(req.code, req.filename)
        if ok:
            return {"status": "ok", "message": msg}
        else:
            raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/skills/install-file")
async def install_skill_file(file: UploadFile = File(...)):
    """Install a .py skill file."""
    if not file.filename or not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="只支持 .py 文件")
    registry = get_skill_registry()
    try:
        content = await file.read()
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".py", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        ok = registry.install_skill(Path(tmp_path))
        Path(tmp_path).unlink(missing_ok=True)
        if ok:
            return {"status": "ok", "message": f"技能 {file.filename} 安装成功"}
        else:
            raise HTTPException(status_code=400, detail="技能安装失败")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/skills/install-zip")
async def install_skill_zip(file: UploadFile = File(...)):
    """Install a .zip skill package."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="只支持 .zip 文件")
    registry = get_skill_registry()
    try:
        content = await file.read()
        import zipfile, subprocess, sys
        with tempfile.TemporaryDirectory() as tmpdir:
            zp = Path(tmpdir) / "s.zip"
            zp.write_bytes(content)
            ed = Path(tmpdir) / "extracted"
            with zipfile.ZipFile(zp, "r") as z:
                z.extractall(ed)
            for req_file in ed.rglob("requirements.txt"):
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                              capture_output=True, text=True)
            installed = 0
            for pyf in ed.rglob("*.py"):
                if pyf.name.startswith("__") or pyf.name.startswith("test_"):
                    continue
                if registry.install_skill(pyf):
                    installed += 1
            if installed:
                return {"status": "ok", "message": f"安装了 {installed} 个技能"}
            else:
                raise HTTPException(status_code=400, detail="未找到有效技能")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/skills/{name}")
async def uninstall_skill(name: str):
    registry = get_skill_registry()
    try:
        registry.uninstall_skill(name)
        return {"status": "ok", "message": f"技能 {name} 已卸载"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))