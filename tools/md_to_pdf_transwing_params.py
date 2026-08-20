#!/usr/bin/env python3
"""Generate PDF from Transwing multirotor parameter markdown."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "docs" / "Transwing_多旋翼动力与滤波参数配置.md"
PDF_PATH = ROOT / "docs" / "Transwing_多旋翼动力与滤波参数配置.pdf"
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")


def register_fonts() -> str:
    if FONT_PATH.exists():
        pdfmetrics.registerFont(TTFont("YaHei", str(FONT_PATH)))
        return "YaHei"
    pdfmetrics.registerFont(TTFont("SimSun", r"C:\Windows\Fonts\simsun.ttc"))
    return "SimSun"


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


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


def build_pdf(blocks: list, font_name: str) -> None:
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Transwing 多旋翼动力与滤波参数配置",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", fontName=font_name, fontSize=18, leading=24, spaceAfter=10, textColor=colors.HexColor("#1a1a1a"))
    h2 = ParagraphStyle("H2", fontName=font_name, fontSize=14, leading=20, spaceBefore=12, spaceAfter=8, textColor=colors.HexColor("#2c5282"))
    h3 = ParagraphStyle("H3", fontName=font_name, fontSize=12, leading=16, spaceBefore=8, spaceAfter=6, textColor=colors.HexColor("#2d3748"))
    body = ParagraphStyle("Body", fontName=font_name, fontSize=9.5, leading=14, spaceAfter=4)
    quote = ParagraphStyle("Quote", fontName=font_name, fontSize=9, leading=13, leftIndent=12, textColor=colors.HexColor("#4a5568"), spaceAfter=6)
    code_style = ParagraphStyle("CodeHdr", fontName=font_name, fontSize=8, leading=10)

    story = []

    for kind, content in blocks:
        if kind == "h1":
            story.append(Paragraph(esc(content), h1))
        elif kind == "h2":
            story.append(Spacer(1, 6))
            story.append(Paragraph(esc(content), h2))
        elif kind == "h3":
            story.append(Paragraph(esc(content), h3))
        elif kind == "p":
            text = esc(content)
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
            text = re.sub(r"`([^`]+)`", r"<font face='Courier'>\1</font>", text)
            text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<link href="\2" color="blue">\1</link>', text)
            story.append(Paragraph(text, body))
        elif kind == "quote":
            story.append(Paragraph(esc(content), quote))
        elif kind == "hr":
            story.append(Spacer(1, 8))
        elif kind == "ul":
            for item in content:
                item_esc = esc(item)
                item_esc = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", item_esc)
                item_esc = re.sub(r"`([^`]+)`", r"<font face='Courier'>\1</font>", item_esc)
                story.append(Paragraph("• " + item_esc, body))
        elif kind == "code":
            story.append(Spacer(1, 4))
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
            col_count = len(data_rows[0])
            col_width = (17 * cm) / max(col_count, 1)
            table = Table(data_rows, colWidths=[col_width] * col_count, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("FONT", (0, 0), (-1, -1), font_name, 8),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f7")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1a202c")),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e0")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.append(Spacer(1, 4))
            story.append(table)
            story.append(Spacer(1, 6))

    doc.build(story)


def main() -> None:
    font_name = register_fonts()
    blocks = parse_md(MD_PATH)
    build_pdf(blocks, font_name)
    print(f"Wrote {PDF_PATH}")


if __name__ == "__main__":
    main()
