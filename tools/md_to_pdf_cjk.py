#!/usr/bin/env python3
"""Convert a Markdown file to A4 PDF with CJK fonts (reportlab)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

CJK_FONT_CANDIDATES = [
    Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    Path("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
]


def find_cjk_font() -> Path:
    for path in CJK_FONT_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("No CJK font found (install fonts-wqy-microhei or use Windows YaHei)")


def register_fonts() -> str:
    path = find_cjk_font()
    kwargs = {"subfontIndex": 0} if path.suffix.lower() == ".ttc" else {}
    pdfmetrics.registerFont(TTFont("CJK", str(path), **kwargs))
    return "CJK"


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text: str) -> str:
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r"<font name='CJK'><b>\1</b></font>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<link href="\2" color="#2b6cb0">\1</link>', text)
    return text


def parse_md(path: Path) -> list:
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks: list = []
    i = 0
    in_code = False
    code_buf: list[str] = []

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            if in_code:
                blocks.append(("code", "\n".join(code_buf)))
                code_buf = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        if line.startswith("# "):
            blocks.append(("h1", line[2:].strip()))
        elif line.startswith("## "):
            blocks.append(("h2", line[3:].strip()))
        elif line.startswith("### "):
            blocks.append(("h3", line[4:].strip()))
        elif line.startswith("|") and i + 1 < len(lines) and lines[i + 1].startswith("|"):
            table_lines = [line]
            i += 1
            table_lines.append(lines[i])
            i += 1
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            blocks.append(("table", table_lines))
            continue
        elif line.strip() == "---":
            blocks.append(("hr", ""))
        elif line.strip().startswith("- "):
            items = []
            while i < len(lines) and (lines[i].strip().startswith("- ") or lines[i].strip().startswith("  ")):
                if lines[i].strip().startswith("- "):
                    items.append(lines[i].strip()[2:])
                i += 1
            blocks.append(("ul", items))
            continue
        elif line.strip().startswith(">"):
            blocks.append(("quote", line.strip().lstrip("> ").strip()))
        elif line.strip():
            blocks.append(("p", line.strip()))
        i += 1

    return blocks


def table_col_widths(headers: list[str], usable: float) -> list[float]:
    joined = " ".join(headers)
    n = len(headers)
    if n == 2:
        return [usable * 0.38, usable * 0.62]
    if n == 3 and ("值" in joined or "说明" in joined):
        return [usable * 0.28, usable * 0.18, usable * 0.54]
    if n == 4:
        return [usable * 0.22, usable * 0.18, usable * 0.22, usable * 0.38]
    return [usable / n] * n


def add_page_decor(canvas, doc, title: str) -> None:
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#1a365d"))
    canvas.rect(0, A4[1] - 14, A4[0], 14, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("CJK", 8)
    canvas.drawString(2 * cm, A4[1] - 10, title)
    canvas.setFillColor(colors.HexColor("#edf2f7"))
    canvas.rect(0, 0, A4[0], 16, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#4a5568"))
    canvas.drawString(2 * cm, 6, "Transwing 参数表 · 首飞第一阶段")
    canvas.drawRightString(A4[0] - 2 * cm, 6, f"{doc.page}")
    canvas.restoreState()


def build_pdf(blocks: list, pdf_path: Path, title: str) -> None:
    font_name = register_fonts()
    usable = 17 * cm

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title=title,
        author="Transwing",
    )

    h1 = ParagraphStyle(
        "H1",
        fontName=font_name,
        fontSize=16,
        leading=22,
        spaceAfter=8,
        textColor=colors.HexColor("#1a365d"),
        alignment=TA_CENTER,
    )
    h2 = ParagraphStyle(
        "H2",
        fontName=font_name,
        fontSize=12.5,
        leading=18,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#2b6cb0"),
        borderPadding=2,
    )
    h3 = ParagraphStyle(
        "H3",
        fontName=font_name,
        fontSize=11,
        leading=15,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.HexColor("#2d3748"),
    )
    body = ParagraphStyle("Body", fontName=font_name, fontSize=9.2, leading=13.5, spaceAfter=4, alignment=TA_LEFT)
    cell = ParagraphStyle("Cell", fontName=font_name, fontSize=8.2, leading=11.5)
    cell_h = ParagraphStyle(
        "CellH",
        fontName=font_name,
        fontSize=8.2,
        leading=11.5,
        textColor=colors.white,
    )
    quote = ParagraphStyle(
        "Quote",
        fontName=font_name,
        fontSize=8.8,
        leading=13,
        leftIndent=10,
        textColor=colors.HexColor("#4a5568"),
        spaceAfter=6,
    )
    code_style = ParagraphStyle(
        "Code",
        fontName=font_name,
        fontSize=7.4,
        leading=10.2,
        backColor=colors.HexColor("#f7fafc"),
        borderPadding=6,
    )

    story = []
    for kind, content in blocks:
        if kind == "h1":
            story.append(Spacer(1, 6))
            story.append(Paragraph(esc(content), h1))
        elif kind == "h2":
            story.append(Spacer(1, 4))
            story.append(Paragraph(esc(content), h2))
        elif kind == "h3":
            story.append(Paragraph(esc(content), h3))
        elif kind == "p":
            story.append(Paragraph(inline(content), body))
        elif kind == "quote":
            story.append(Paragraph(inline(content), quote))
        elif kind == "hr":
            story.append(Spacer(1, 6))
        elif kind == "ul":
            for item in content:
                story.append(Paragraph("• " + inline(item), body))
        elif kind == "code":
            story.append(Spacer(1, 3))
            story.append(Preformatted(content, code_style))
            story.append(Spacer(1, 6))
        elif kind == "table":
            rows = []
            for tl in content:
                cells = [c.strip() for c in tl.strip("|").split("|")]
                rows.append(cells)
            if len(rows) < 2:
                continue
            data_rows = [rows[0]] + rows[2:]
            widths = table_col_widths(data_rows[0], usable)
            formatted = []
            for r_i, row in enumerate(data_rows):
                style = cell_h if r_i == 0 else cell
                formatted.append([Paragraph(inline(c), style) for c in row])
            table = Table(formatted, colWidths=widths, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b6cb0")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#a0aec0")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ebf8ff")]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                    ]
                )
            )
            story.append(Spacer(1, 3))
            story.append(table)
            story.append(Spacer(1, 8))

    def on_page(canvas, doc_):
        add_page_decor(canvas, doc_, title)

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


def main() -> int:
    parser = argparse.ArgumentParser(description="Markdown → CJK PDF")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    md_path = args.input.resolve()
    if not md_path.exists():
        print(f"Input not found: {md_path}", file=sys.stderr)
        return 1

    pdf_path = (args.output or md_path.with_suffix(".pdf")).resolve()
    blocks = parse_md(md_path)
    title = next((c for k, c in blocks if k == "h1"), md_path.stem)
    build_pdf(blocks, pdf_path, title)
    print(f"Wrote {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
