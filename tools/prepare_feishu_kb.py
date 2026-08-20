#!/usr/bin/env python3
"""Export Transwing knowledge-base files by category for Feishu upload.

Output: outputs/feishu-kb-export/<category>/
  - Markdown/CSV/params copied or converted to .txt for Feishu local upload
  - manifest.json with paths and titles

Usage:
  python tools/prepare_feishu_kb.py
  python tools/prepare_feishu_kb.py --open   # open export folder on Windows
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    raise SystemExit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO_ROOT / "knowledge-base" / "index.yaml"
DEFAULT_OUT = REPO_ROOT / "outputs" / "feishu-kb-export"

# Feishu 知识问答 / Aily 本地上传常见格式
FEISHU_UPLOAD_EXT = {".txt", ".pdf", ".docx", ".doc", ".pptx", ".ppt"}
CONVERT_TO_TXT = {".md", ".csv", ".params", ".lua", ".mjs"}


def safe_dirname(title: str) -> str:
    return title.replace("/", "-").replace("\\", "-").strip()


def export_item(src: Path, dst_dir: Path, title: str) -> Path | None:
    if not src.is_file():
        return None

    ext = src.suffix.lower()
    base = safe_dirname(src.stem) or "untitled"

    if ext in FEISHU_UPLOAD_EXT:
        dst = dst_dir / f"{base}{ext}"
        shutil.copy2(src, dst)
        return dst

    if ext in CONVERT_TO_TXT:
        dst = dst_dir / f"{base}.txt"
        header = f"# {title}\n# source: {src.relative_to(REPO_ROOT).as_posix()}\n\n"
        body = src.read_text(encoding="utf-8", errors="replace")
        dst.write_text(header + body, encoding="utf-8")
        return dst

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Export KB by category for Feishu")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output directory")
    parser.add_argument("--open", action="store_true", help="Open output folder (Windows)")
    args = parser.parse_args()

    if not INDEX_PATH.is_file():
        print(f"Missing index: {INDEX_PATH}", file=sys.stderr)
        return 1

    with INDEX_PATH.open(encoding="utf-8") as f:
        index = yaml.safe_load(f)

    out_root: Path = args.out
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)

    manifest: dict = {"categories": [], "files": [], "feishu_notes": []}

    for block in index.get("categories", []):
        cat_id = block.get("id", "misc")
        cat_title = block.get("title", cat_id)
        cat_dir = out_root / f"{cat_id}_{safe_dirname(cat_title)}"
        cat_dir.mkdir(parents=True)

        cat_entry = {"id": cat_id, "title": cat_title, "folder": cat_dir.name, "items": []}

        for item in block.get("items", []):
            rel = item.get("path", "")
            src = REPO_ROOT / rel.replace("/", "\\") if "\\" not in rel else REPO_ROOT / rel
            if not src.is_file():
                src = REPO_ROOT / rel
            title = item.get("title", src.name)
            dst = export_item(src, cat_dir, title)
            if dst:
                cat_entry["items"].append(
                    {
                        "title": title,
                        "source": rel,
                        "export": dst.relative_to(out_root).as_posix(),
                    }
                )
                manifest["files"].append(str(dst.relative_to(out_root)))

        manifest["categories"].append(cat_entry)

    readme = out_root / "00_上传说明.txt"
    readme.write_text(
        """Transwing → 飞书知识库 导出包
================================

本目录按 knowledge-base/index.yaml 自动分类，供飞书上传。

【本机飞书】C:\\Users\\alu\\AppData\\Local\\Feishu\\Feishu.exe

方式 A — 知识问答（最简单，自动向量化）
  1. 打开飞书 → 左侧「知识问答」
  2. 点击「上传」或对话里 + → 上传文件
  3. 按子文件夹分批上传（机体/固件/SITL…）
  4. 上传后飞书云端自动解析、切片、向量化（无需本地操作）
  5. 提问时在「知识范围」勾选对应资料

方式 B — 飞书 Wiki 知识库（手动分类 + 知识问答可检索）
  1. 云文档 → 知识库 → 新建「Transwing 研发知识库」
  2. 按本目录子文件夹名建同级节点（01 机体与建模 …）
  3. 各节点下：新建文档 → 导入 / 粘贴对应 .txt 内容
  4. 知识问答 → 指定范围 → 选择该 Wiki 节点

方式 C — Aily 智能伙伴（企业版，可自定义切片）
  1. 飞书 Aily 控制台 → 知识库 → 添加数据 → 本地文件
  2. 选「自动分段」→ 系统自动向量化
  3. 可预览切片、调整召回参数

注意：
  - 向量化在飞书云端完成，本地客户端只负责上传
  - .params/.csv 已转为 .txt 便于上传；精确参数仍以 Git 源文件为准
  - 更新文档后需重新导出并上传/覆盖，或改 Wiki 源文档

详细步骤见：knowledge-base/FEISHU_GUIDE.md
""",
        encoding="utf-8",
    )

    manifest_path = out_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    total = len(manifest["files"])
    print(f"Exported {total} files to {out_root}")
    for cat in manifest["categories"]:
        print(f"  [{cat['id']}] {cat['title']}: {len(cat['items'])} files")

    if args.open and sys.platform == "win32":
        subprocess.run(["explorer", str(out_root)], check=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
