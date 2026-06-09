"""Office Export Skill — Export reports to Word (.docx) with optional PDF conversion.

Workflow:
  Always generate .docx first. If PDF requested, convert .docx -> PDF via LibreOffice.
  Inline markdown formatting (**bold**, *italic*, `code`, [links](url)) is properly
  rendered in Word output - no raw markdown symbols leak through.
"""
import re
import subprocess
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from src.skills.base import BaseSkill, SkillResult, SkillContext

OUTPUT_DIR = Path.home() / ".cs599-agent" / "output"


# ---------------------------------------------------------------------------
# Inline markdown -> python-docx runs
# ---------------------------------------------------------------------------


def _apply_inline_md(paragraph, text: str):
    """Parse inline markdown tokens in *text* and add formatted runs to *paragraph*.

    Supported: **bold**  *italic*  `code`  [link](url)  ~~strikethrough~~
    """
    from docx.shared import Pt, RGBColor

    pattern = re.compile(
        r'\*\*(.+?)\*\*'                             # **bold**
        r'|\*(.+?)\*'                                # *italic*
        r'|`(.+?)`'                                   # `code`
        r'|\[(.+?)\]\((.+?)\)'                       # [link](url)
        r'|~~(.+?)~~'                                 # ~~strikethrough~~
    )

    last_end = 0
    for m in pattern.finditer(text):
        if m.start() > last_end:
            run = paragraph.add_run(text[last_end:m.start()])
            run.font.name = 'Times New Roman'
            run.font.size = Pt(11)

        run = None
        grp1, grp2, grp3, grp4, grp5, grp6 = m.groups()
        if grp1:      # **bold**
            run = paragraph.add_run(grp1)
            run.bold = True
        elif grp2:    # *italic*
            run = paragraph.add_run(grp2)
            run.italic = True
        elif grp3:    # `code`
            run = paragraph.add_run(grp3)
            run.font.name = 'Consolas'
            run.font.size = Pt(9)
        elif grp4:    # [link](url)
            run = paragraph.add_run(grp4)
            run.font.color.rgb = RGBColor(0, 102, 204)
            run.underline = True
        elif grp6:    # ~~strikethrough~~
            run = paragraph.add_run(grp6)
            run.font.strike = True

        if run is not None:
            run.font.name = run.font.name or 'Times New Roman'
            run.font.size = run.font.size or Pt(11)

        last_end = m.end()

    if last_end < len(text):
        run = paragraph.add_run(text[last_end:])
        run.font.name = 'Times New Roman'
        run.font.size = Pt(11)


def _add_plain_para(doc, text: str, style=None):
    """Add an empty paragraph with the given style, then apply inline markdown."""
    p = doc.add_paragraph(style=style)
    if text:
        _apply_inline_md(p, text)
    return p


# ── DOCX generation ──────────────────────────────────────────────────────────
def _render_docx(markdown_text: str, title: str, author: str, language: str) -> Path:
    """Convert Markdown to .docx using python-docx."""
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    doc = Document()

    # ── Default style ──
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(11)
    pf = style.paragraph_format
    pf.space_after = Pt(6)
    pf.line_spacing = 1.15
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

    # ── Title page ──
    for _ in range(6):
        doc.add_paragraph('')
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = tp.add_run(title or "Research Report")
    r.bold = True
    r.font.size = Pt(24)
    r.font.name = 'Times New Roman'
    r.font.color.rgb = RGBColor(30, 30, 80)

    doc.add_paragraph('')
    if author:
        ap = doc.add_paragraph()
        ap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ar = ap.add_run(f"Author: {author}")
        ar.font.size = Pt(14)
        ar.font.name = 'Times New Roman'
        ar.font.color.rgb = RGBColor(60, 60, 60)

    doc.add_paragraph('')
    dp = doc.add_paragraph()
    dp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dr = dp.add_run(datetime.now().strftime("%B %d, %Y"))
    dr.font.size = Pt(12)
    dr.font.name = 'Times New Roman'
    dr.font.color.rgb = RGBColor(100, 100, 100)

    # Generate abstract (first 300 chars of content as summary)
    plain = re.sub(r'[#*>|`\-\[\]]', '', markdown_text)[:300]
    if plain:
        doc.add_paragraph('')
        ab = doc.add_paragraph()
        ab.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ab_lab = ab.add_run("Abstract")
        ab_lab.bold = True
        ab_lab.font.size = Pt(12)
        ab_lab.font.name = 'Times New Roman'
        doc.add_paragraph('')
        ap = doc.add_paragraph()
        ap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ap_r = ap.add_run(plain + "...")
        ap_r.font.size = Pt(10)
        ap_r.font.name = 'Times New Roman'
        ap_r.font.color.rgb = RGBColor(80, 80, 80)

    doc.add_page_break()

    # ── Markdown parser ──
    lines = markdown_text.split('\n')
    i = 0
    in_code = False
    code_buf: List[str] = []
    in_table = False
    table_buf: List[str] = []

    def flush_code():
        if not code_buf:
            return
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
        pf = p.paragraph_format
        pf.left_indent = Inches(0.3)
        # Add shading
        shading = OxmlElement('w:shd')
        shading.set(qn('w:fill'), 'F0F0F0')
        shading.set(qn('w:val'), 'clear')
        p.paragraph_format.element.get_or_add_pPr().append(shading)
        for cl in code_buf:
            r = p.add_run(cl + '\n')
            r.font.name = 'Consolas'
            r.font.size = Pt(9)
            r.font.color.rgb = RGBColor(50, 50, 50)
        code_buf.clear()

    def flush_table():
        if len(table_buf) < 2:
            table_buf.clear()
            return
        rows_data = []
        for line in table_buf:
            if line.strip().startswith('|') and line.strip().endswith('|'):
                cols = [c.strip() for c in line.split('|')[1:-1]]
                rows_data.append(cols)
        if not rows_data:
            table_buf.clear()
            return
        # Determine columns
        max_cols = max(len(r) for r in rows_data)
        table = doc.add_table(rows=len(rows_data)-1, cols=max_cols)
        table.style = 'Table Grid'
        # Header
        header = rows_data[0]
        for j, h in enumerate(header):
            cell = table.rows[0].cells[j]
            cell.text = h
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.bold = True
                    run.font.size = Pt(10)
            # Shading for header
            shading = OxmlElement('w:shd')
            shading.set(qn('w:fill'), 'D9E2F3')
            shading.set(qn('w:val'), 'clear')
            cell._tc.get_or_add_tcPr().append(shading)
        # Data rows (skip separator line and header)
        row_idx = 1
        for ri in range(2, len(rows_data)):
            if ri < len(rows_data) and row_idx < len(table.rows):
                for j, val in enumerate(rows_data[ri]):
                    if j < len(table.rows[row_idx].cells):
                        table.rows[row_idx].cells[j].text = val
                row_idx += 1
        table_buf.clear()

    while i < len(lines):
        line = lines[i]

        # Code block
        if line.strip().startswith('```'):
            if in_code:
                in_code = False
                flush_code()
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # Flush table if we encounter a non-table line
        if in_table and not (line.strip().startswith('|') and line.strip().endswith('|')):
            in_table = False
            flush_table()

        # Table
        if line.strip().startswith('|') and line.strip().endswith('|'):
            # Skip separator line (|---|---|)
            if not re.match(r'^\|[\s\-:]+\|', line):
                in_table = True
                table_buf.append(line)
            i += 1
            continue

        # Heading 1
        if line.startswith('# ') and not line.startswith('## '):
            h = doc.add_heading(line[2:], level=1)
            for run in h.runs:
                run.font.name = 'Times New Roman'
        # Heading 2
        elif line.startswith('## ') and not line.startswith('### '):
            h = doc.add_heading(line[3:], level=2)
            for run in h.runs:
                run.font.name = 'Times New Roman'
        # Heading 3
        elif line.startswith('### '):
            h = doc.add_heading(line[4:], level=3)
            for run in h.runs:
                run.font.name = 'Times New Roman'
        # Blockquote (with inline formatting)
        elif line.startswith('> '):
            p = doc.add_paragraph()
            _apply_inline_md(p, line[2:])
            for run in p.runs:
                run.italic = True
            ppf = p.paragraph_format
            ppf.left_indent = Inches(0.3)
            pPr = p._p.get_or_add_pPr()
            pBdr = OxmlElement('w:pBdr')
            left = OxmlElement('w:left')
            left.set(qn('w:val'), 'single')
            left.set(qn('w:sz'), '12')
            left.set(qn('w:color'), '888888')
            pBdr.append(left)
            pPr.append(pBdr)
        # List item (with inline formatting)
        elif re.match(r'^[\-\*]\s', line):
            _add_plain_para(doc, line[2:], style='List Bullet')
        elif re.match(r'^\d+\.\s', line):
            _add_plain_para(doc, re.sub(r'^\d+\.\s', '', line), style='List Number')
        # Empty line
        # Image ![alt](path)
        elif (match_img := re.match(r'!\[(.*?)\]\((.+?)\)', line.strip())):
            img_alt = match_img.group(1)
            img_path = match_img.group(2)
            try:
                from docx.shared import Inches as _Inches
                # Resolve relative path against OUTPUT_DIR parent
                abs_path = Path(img_path)
                if not abs_path.is_absolute():
                    abs_path = OUTPUT_DIR.parent / img_path
                if abs_path.exists():
                    # Add image centered
                    img_para = doc.add_paragraph()
                    img_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = img_para.add_run()
                    run.add_picture(str(abs_path), width=_Inches(5.0))
                    # Add caption below image
                    if img_alt:
                        cap = doc.add_paragraph()
                        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        cap_r = cap.add_run(img_alt)
                        cap_r.font.size = Pt(9)
                        cap_r.font.name = 'Times New Roman'
                        cap_r.italic = True
                        cap_r.font.color.rgb = RGBColor(80, 80, 80)
                else:
                    # Image file not found — fall back to text
                    _add_plain_para(doc, f"[Image: {img_alt}] ({img_path})")
            except Exception:
                _add_plain_para(doc, f"[Image: {img_alt}]")
        # Empty line
        elif line.strip() == '':
            pass
        # Regular paragraph (with inline formatting)
        else:
            _add_plain_para(doc, line)

        i += 1

    if in_code:
        flush_code()
    if in_table:
        flush_table()

    # ── Save ──
    safe_title = re.sub(r'[^\w\s\-]', '', title)[:40] or "report"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{safe_title}_{ts}.docx"
    doc.save(str(path))
    return path


# ── DOCX → PDF conversion (via LibreOffice) ────────────────────────────────

def _convert_docx_to_pdf(docx_path: Path) -> Optional[Path]:
    """Convert .docx → PDF using LibreOffice headless CLI.

    Returns the PDF path on success, or *None* if conversion fails.
    """
    pdf_path = docx_path.with_suffix('.pdf')
    try:
        subprocess.run(
            ['libreoffice', '--headless', '--convert-to', 'pdf',
             '--outdir', str(OUTPUT_DIR), str(docx_path)],
            check=True, capture_output=True, timeout=120,
        )
        return pdf_path if pdf_path.exists() else None
    except (subprocess.CalledProcessError, FileNotFoundError,
            subprocess.TimeoutExpired):
        return None


# ── Skill class ──────────────────────────────────────────────────────────────
class OfficeExportSkill(BaseSkill):
    """Export markdown content to Word (.docx).  Optionally convert to PDF.

    Workflow:
      1. Always generate .docx (with proper inline formatting).
      2. If ``format="pdf"``, convert .docx → PDF via LibreOffice.
      3. Return the download URL of the final file.
    """
    name = "office_export"
    display_name = "学术文档导出"
    description = "将研究报告/论文导出为 Word (.docx) 格式，或进一步转为 PDF。"
    version = "1.1.0"
    author = "CS599 Agent"
    tags = ["export", "office", "word", "pdf"]

    parameters_schema = {
        "content": {"type": "string",
                     "description": "要导出的 Markdown 内容", "required": True},
        "format": {"type": "string",
                    "description": "输出格式", "options": ["docx", "pdf"],
                    "default": "docx"},
        "title": {"type": "string",
                   "description": "文档标题", "default": "Research Report"},
        "author": {"type": "string",
                    "description": "作者名",
                    "default": "CS599 Research Assistant"},
        "language": {"type": "string",
                      "description": "语言", "options": ["en", "zh"],
                      "default": "en"},
    }

    def execute(self, context: SkillContext) -> SkillResult:
        content = context.custom_params.get("content", "")
        fmt = context.custom_params.get("format", "docx")
        title = context.custom_params.get("title", "Research Report")
        author = context.custom_params.get(
            "author", "CS599 Research Assistant")
        language = context.custom_params.get("language", "en")

        if not content:
            return SkillResult(success=False, error="No content provided")

        if len(content) < 100:
            content = f"# {title}\n\n{content}"

        try:
            # Step 1: always generate .docx
            docx_path = _render_docx(content, title, author, language)
            path = docx_path

            # Step 2: optionally convert to PDF
            if fmt == "pdf":
                pdf_path = _convert_docx_to_pdf(docx_path)
                if pdf_path:
                    path = pdf_path

            filename = path.name
            download_url = f"/api/download/{filename}"

            return SkillResult(
                success=True,
                content=download_url,
                metadata={
                    "filename": filename,
                    "format": "pdf" if (fmt == "pdf" and path.suffix == ".pdf") else "docx",
                    "path": str(path),
                    "size": path.stat().st_size,
                },
            )
        except ImportError as e:
            missing = str(e).split("'")[1] if "'" in str(e) else str(e)
            return SkillResult(
                success=False,
                error=f"缺少依赖库: {missing}。请运行: pip install python-docx fpdf2",
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))