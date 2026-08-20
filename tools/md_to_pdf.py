#!/usr/bin/env python3
"""Convert a Markdown file to PDF with Chinese font support (fpdf2)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from fpdf import FPDF


def find_cjk_font() -> Path:
    candidates = [
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("No CJK font found under C:\\Windows\\Fonts")


class MarkdownPDF(FPDF):
    def __init__(self, font_path: Path) -> None:
        super().__init__()
        self.font_path = font_path
        self._font_ready = False
        self.margin_l = 18
        self.margin_r = 18
        self.margin_t = 16
        self.margin_b = 16
        self.set_margins(self.margin_l, self.margin_t, self.margin_r)
        self.set_auto_page_break(auto=True, margin=self.margin_b)

    def setup_font(self) -> None:
        if self._font_ready:
            return
        self.add_font("CJK", "", str(self.font_path))
        self._font_ready = True

    def use(self, size: float, style: str = "") -> None:
        self.setup_font()
        self.set_font("CJK", size=size)

    def write_line(self, text: str, size: float = 10, gap: float = 1.5) -> None:
        self.use(size)
        self.multi_cell(0, gap * size / 2.8, text)
        self.ln(1)

    def write_heading(self, text: str, level: int) -> None:
        sizes = {1: 16, 2: 13, 3: 11}
        self.ln(2 if level == 1 else 1)
        self.write_line(text, sizes.get(level, 11), gap=1.6)
        if level == 1:
            self.ln(1)

    def write_code_block(self, lines: list[str]) -> None:
        self.use(8.5)
        x = self.get_x()
        y = self.get_y()
        w = self.w - self.margin_l - self.margin_r
        h = max(6, len(lines) * 4.2 + 4)
        if y + h > self.h - self.margin_b:
            self.add_page()
            y = self.get_y()
        self.set_fill_color(245, 245, 245)
        self.rect(x, y, w, h, style="F")
        self.set_xy(x + 2, y + 2)
        for line in lines:
            self.multi_cell(w - 4, 4.2, line)
        self.set_xy(x, y + h + 2)

    def write_table(self, rows: list[list[str]]) -> None:
        if not rows:
            return
        col_count = max(len(r) for r in rows)
        w = self.w - self.margin_l - self.margin_r
        col_w = w / col_count
        self.use(8.5)
        for row in rows:
            if self.get_y() > self.h - self.margin_b - 8:
                self.add_page()
            x0 = self.get_x()
            y0 = self.get_y()
            max_h = 0.0
            cell_lines: list[list[str]] = []
            for i in range(col_count):
                cell = row[i] if i < len(row) else ""
                cell = re.sub(r"\*\*(.+?)\*\*", r"\1", cell)
                self.set_xy(x0 + i * col_w + 1, y0 + 1)
                lines = self.multi_cell(col_w - 2, 4.0, cell, split_only=True)
                cell_lines.append(lines)
                max_h = max(max_h, len(lines) * 4.0 + 2)
            for i in range(col_count):
                x = x0 + i * col_w
                self.rect(x, y0, col_w, max_h)
                self.set_xy(x + 1, y0 + 1)
                for line in cell_lines[i]:
                    self.cell(col_w - 2, 4.0, line, ln=1)
            self.set_xy(x0, y0 + max_h)


def parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    i = start
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("|"):
            break
        if re.match(r"^\|[-:\s|]+\|$", line):
            i += 1
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
        i += 1
    return rows, i


def md_to_pdf(md_path: Path, pdf_path: Path) -> None:
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    font_path = find_cjk_font()

    pdf = MarkdownPDF(font_path)
    pdf.add_page()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped == "---":
            pdf.ln(2)
            i += 1
            continue

        if stripped.startswith("```"):
            i += 1
            block: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i].rstrip())
                i += 1
            if i < len(lines):
                i += 1
            pdf.write_code_block(block)
            continue

        if stripped.startswith("|"):
            rows, i = parse_table(lines, i)
            pdf.write_table(rows)
            pdf.ln(2)
            continue

        m = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if m:
            pdf.write_heading(m.group(2).strip(), len(m.group(1)))
            i += 1
            continue

        if stripped.startswith("- "):
            items: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append("- " + lines[i].strip()[2:])
                i += 1
            for item in items:
                pdf.write_line(item, 9.5)
            continue

        para = stripped
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if (
                not nxt
                or nxt.startswith("#")
                or nxt.startswith("|")
                or nxt.startswith("```")
                or nxt.startswith("- ")
                or nxt == "---"
            ):
                break
            para += " " + nxt
            i += 1
        para = re.sub(r"\*\*(.+?)\*\*", r"\1", para)
        para = re.sub(r"`([^`]+)`", r"\1", para)
        pdf.write_line(para, 10)

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(pdf_path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Markdown to PDF")
    parser.add_argument("input", type=Path, help="Input .md file")
    parser.add_argument("-o", "--output", type=Path, help="Output .pdf file")
    args = parser.parse_args()

    md_path = args.input.resolve()
    if not md_path.exists():
        print(f"Input not found: {md_path}", file=sys.stderr)
        return 1

    pdf_path = args.output or md_path.with_suffix(".pdf")
    md_to_pdf(md_path, pdf_path.resolve())
    print(f"Wrote {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
