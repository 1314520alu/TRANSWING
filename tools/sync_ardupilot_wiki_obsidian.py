#!/usr/bin/env python3
"""Sync ArduPilot wiki (Git RST) into an Obsidian vault as Markdown.

Usage:
  python tools/sync_ardupilot_wiki_obsidian.py
  python tools/sync_ardupilot_wiki_obsidian.py --vault "C:\\Users\\alu\\Documents\\ArduPilot Wiki"
  python tools/sync_ardupilot_wiki_obsidian.py --update
  python tools/sync_ardupilot_wiki_obsidian.py --relink-only
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE = REPO_ROOT / ".cache" / "ardupilot_wiki"
DEFAULT_VAULT = Path(r"C:\Users\alu\Documents\ArduPilot Wiki")
DEFAULT_MANIFEST_DIR = REPO_ROOT / "outputs" / "ardupilot-obsidian-sync"
WIKI_GIT_URL = "https://github.com/ArduPilot/ardupilot_wiki.git"

SITE_TITLES = {
    "ardupilot": "ArduPilot",
    "antennatracker": "Antenna Tracker",
    "blimp": "Blimp",
    "common": "Common Topics",
    "copter": "Copter",
    "dev": "Developer",
    "mavproxy": "MAVProxy",
    "plane": "Plane / QuadPlane",
    "planner": "Mission Planner",
    "planner2": "APM Planner 2",
    "rover": "Rover",
    "sub": "Sub",
}

ANCHOR_RE = re.compile(r"^\.\.\s+_([^:\s]+):\s*$", re.MULTILINE)
TOCTREE_BLOCK_RE = re.compile(
    r"(?P<indent>\.\.)\s+toctree::\s*\n"
    r"(?P<options>(?:\s+:[^\n]+\n)*)"
    r"(?P<entries>(?:\s+[^\n]+\n)+)",
    re.MULTILINE,
)
REF_ROLE_RE = re.compile(
    r"(?::ref:|\{ref\})`(?P<label>[^`<]+?)(?:\s*<(?P<anchor>[^>]+)>)?`"
)
DOC_ROLE_RE = re.compile(
    r"(?::doc:|\{doc\})`(?P<label>[^`<]+?)(?:\s*<(?P<path>[^>]+)>)?`"
)
MD_LINK_ANCHOR_RE = re.compile(r"\[([^\]]+)\]\(#([^)]+)\)")
IMG_MD_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
IMAGE_PATH_RE = re.compile(r"(?:\.\./)+images/([^\s)\"']+)", re.IGNORECASE)
MYST_IMAGE_RE = re.compile(
    r"```\{image\}\s+([^\n`]+)\n(?::target:[^\n]*\n)?```",
    re.MULTILINE,
)


@dataclass
class WikiContext:
    wiki_root: Path
    vault: Path
    commit: str
    sites: list[str] = field(default_factory=list)
    anchor_map: dict[str, str] = field(default_factory=dict)
    doc_map: dict[str, str] = field(default_factory=dict)
    unresolved: list[tuple[str, str, str]] = field(default_factory=list)
    converted: int = 0
    skipped: int = 0
    relinked: int = 0


def _subprocess_env() -> dict[str, str]:
    import os

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def sync_wiki_repo(cache: Path, update: bool) -> str:
    if (cache / ".git").is_dir():
        if update:
            print(f"Updating wiki cache: {cache}")
            result = run_git(["pull", "--ff-only"], cache)
            if result.returncode != 0:
                print(result.stderr or result.stdout, file=sys.stderr)
                raise SystemExit(1)
        else:
            print(f"Using existing wiki cache: {cache}")
    else:
        cache.parent.mkdir(parents=True, exist_ok=True)
        print(f"Cloning {WIKI_GIT_URL} -> {cache}")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", WIKI_GIT_URL, str(cache)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            print(result.stderr or result.stdout, file=sys.stderr)
            raise SystemExit(1)

    rev = run_git(["rev-parse", "--short", "HEAD"], cache)
    if rev.returncode != 0:
        raise SystemExit(f"Cannot read wiki commit in {cache}")
    return rev.stdout.strip()


def discover_sites(wiki_root: Path) -> list[str]:
    sites: list[str] = []
    for child in sorted(wiki_root.iterdir()):
        if child.is_dir() and (child / "source" / "docs").is_dir():
            sites.append(child.name)
    return sites


def vault_site_for(site: str) -> str:
    return site


def vault_rel_path(site: str, stem: str) -> str:
    return f"{vault_site_for(site)}/{stem}.md"


def web_url(site: str, stem: str) -> str:
    return f"https://ardupilot.org/{site}/docs/{stem}.html"


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_state(manifest_dir: Path) -> dict:
    path = manifest_dir / "state.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_state(manifest_dir: Path, state: dict) -> None:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def scan_anchors_and_docs(ctx: WikiContext) -> None:
    for site in ctx.sites:
        docs_dir = ctx.wiki_root / site / "source" / "docs"
        for rst in docs_dir.rglob("*.rst"):
            rel = rst.relative_to(docs_dir)
            stem = rel.with_suffix("").as_posix().replace("\\", "/")
            vault_rel = vault_rel_path(vault_site_for(site), stem)
            ctx.doc_map[f"{site}/{stem}"] = vault_rel
            ctx.doc_map[stem] = vault_rel
            if site == "common" and stem.startswith("common-"):
                ctx.doc_map[stem[len("common-") :]] = vault_rel

            text = rst.read_text(encoding="utf-8", errors="replace")
            for match in ANCHOR_RE.finditer(text):
                anchor = match.group(1).strip()
                if anchor not in ctx.anchor_map:
                    ctx.anchor_map[anchor] = vault_rel
                elif site == "common":
                    ctx.anchor_map[anchor] = vault_rel


def rst_to_markdown(rst_path: Path) -> str:
    raw = rst_path.read_bytes().replace(b"\x00", b"")
    tmp = rst_path.with_suffix(".sanitized.rst")
    try:
        tmp.write_bytes(raw)
        result = subprocess.run(
            ["rst2myst", "convert", "--no-sphinx", str(tmp)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_subprocess_env(),
        )
        md_path = tmp.with_suffix(".md")
        if result.returncode == 0 and md_path.is_file():
            content = md_path.read_text(encoding="utf-8", errors="replace")
            md_path.unlink(missing_ok=True)
            return content

        stream = subprocess.run(
            ["rst2myst", "stream", "--no-sphinx", str(tmp)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_subprocess_env(),
        )
        if stream.returncode == 0 and stream.stdout.strip():
            return stream.stdout
        raise RuntimeError(result.stderr or stream.stderr or result.stdout or "rst2myst failed")
    finally:
        tmp.unlink(missing_ok=True)
        tmp.with_suffix(".md").unlink(missing_ok=True)


def image_path_for_vault(from_vault_rel: str, image_name: str) -> str:
    from_dir = Path(from_vault_rel).parent.as_posix()
    if from_dir == ".":
        prefix = ""
    else:
        prefix = "../" * (from_dir.count("/") + 1)
    return f"{prefix}_assets/images/{image_name}"


def fix_images(body: str, vault_rel: str) -> str:
    def repl_myst_image(match: re.Match[str]) -> str:
        src = match.group(1).strip()
        m = IMAGE_PATH_RE.search(src)
        if m:
            src = image_path_for_vault(vault_rel, m.group(1))
        elif "/images/" in src:
            src = image_path_for_vault(vault_rel, Path(src).name)
        return f"![]({src})"

    body = MYST_IMAGE_RE.sub(repl_myst_image, body)
    def repl_path(match: re.Match[str]) -> str:
        return image_path_for_vault(vault_rel, match.group(1))

    body = IMAGE_PATH_RE.sub(repl_path, body)

    def repl_md(match: re.Match[str]) -> str:
        alt, src = match.group(1), match.group(2)
        if src.startswith(("http://", "https://", "data:")):
            return match.group(0)
        m = IMAGE_PATH_RE.search(src)
        if m:
            src = image_path_for_vault(vault_rel, m.group(1))
        elif "/images/" in src:
            src = image_path_for_vault(vault_rel, Path(src).name)
        return f"![{alt}]({src})"

    return IMG_MD_RE.sub(repl_md, body)


def wikilink_for(vault_rel: str, label: str | None = None) -> str:
    target = vault_rel.replace("\\", "/")
    if target.endswith(".md"):
        target = target[:-3]
    if label and label.strip() and label.strip() != target.split("/")[-1]:
        return f"[[{target}|{label.strip()}]]"
    return f"[[{target}]]"


def resolve_anchor(ctx: WikiContext, anchor: str, source_vault_rel: str) -> str | None:
    anchor = anchor.strip()
    if anchor in ctx.anchor_map:
        return ctx.anchor_map[anchor]
    stem = anchor.split("/")[-1]
    if stem in ctx.anchor_map:
        return ctx.anchor_map[stem]
    common_key = f"common/{stem}"
    if common_key in ctx.doc_map:
        return ctx.doc_map[common_key]
    if stem in ctx.doc_map:
        return ctx.doc_map[stem]
    return None


def resolve_doc(ctx: WikiContext, doc_path: str) -> str | None:
    doc_path = doc_path.strip().replace("\\", "/")
    if doc_path.endswith(".rst"):
        doc_path = doc_path[:-4]
    candidates = [
        doc_path,
        f"common/{doc_path}",
        doc_path.split("/")[-1],
    ]
    for key in candidates:
        if key in ctx.doc_map:
            return ctx.doc_map[key]
    return None


def fix_links(ctx: WikiContext, body: str, source_vault_rel: str) -> str:
    def repl_ref(match: re.Match[str]) -> str:
        label = (match.group("label") or "").strip()
        anchor = (match.group("anchor") or label).strip()
        target = resolve_anchor(ctx, anchor, source_vault_rel)
        if target:
            return wikilink_for(target, label if match.group("anchor") else None)
        ctx.unresolved.append((source_vault_rel, "ref", anchor))
        return match.group(0)

    body = REF_ROLE_RE.sub(repl_ref, body)

    def repl_doc(match: re.Match[str]) -> str:
        label = (match.group("label") or "").strip()
        path = (match.group("path") or label).strip()
        target = resolve_doc(ctx, path)
        if target:
            return wikilink_for(target, label if match.group("path") else None)
        ctx.unresolved.append((source_vault_rel, "doc", path))
        return match.group(0)

    body = DOC_ROLE_RE.sub(repl_doc, body)

    def repl_md_anchor(match: re.Match[str]) -> str:
        label, anchor = match.group(1), match.group(2)
        target = resolve_anchor(ctx, anchor, source_vault_rel)
        if target:
            return wikilink_for(target, label)
        ctx.unresolved.append((source_vault_rel, "md_anchor", anchor))
        return match.group(0)

    return MD_LINK_ANCHOR_RE.sub(repl_md_anchor, body)


def frontmatter(ctx: WikiContext, site: str, rst_rel: str, stem: str) -> str:
    lines = [
        "---",
        "source: ardupilot_wiki",
        f"site: {site}",
        f"rst_path: {rst_rel}",
        f"web_url: {web_url(site, stem)}",
        f"wiki_commit: {ctx.commit}",
        "license: CC-BY-SA-3.0",
        "---",
        "",
    ]
    return "\n".join(lines)


def postprocess_body(ctx: WikiContext, body: str, vault_rel: str) -> str:
    body = fix_images(body, vault_rel)
    body = fix_links(ctx, body, vault_rel)
    return body


def ensure_vault_skeleton(vault: Path) -> None:
    vault.mkdir(parents=True, exist_ok=True)
    (vault / "_meta").mkdir(exist_ok=True)
    (vault / "_assets" / "images").mkdir(parents=True, exist_ok=True)

    license_path = vault / "_meta" / "LICENSE.md"
    if not license_path.exists():
        license_path.write_text(
            """# ArduPilot Wiki License

This vault mirrors content from [ArduPilot/ardupilot_wiki](https://github.com/ArduPilot/ardupilot_wiki).

**License:** Creative Commons Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0)

- You may share and adapt the material with attribution.
- Derivatives must use the same license.
- Official source: https://ardupilot.org

Full license text: https://creativecommons.org/licenses/by-sa/3.0/legalcode
""",
            encoding="utf-8",
        )


def copy_images(wiki_root: Path, vault: Path) -> int:
    src = wiki_root / "images"
    dst = vault / "_assets" / "images"
    if not src.is_dir():
        return 0
    count = 0
    for path in src.rglob("*"):
        if path.is_file():
            rel = path.relative_to(src)
            out = dst / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            if not out.exists() or path.stat().st_mtime_ns > out.stat().st_mtime_ns:
                shutil.copy2(path, out)
            count += 1
    return count


def parse_toctree_entry_line(line: str) -> tuple[str, str]:
    line = line.strip()
    if not line or line.startswith(":"):
        return "", ""
    match = re.match(r"(.+?)\s*<([^>]+)>", line)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return line, line


def parse_toctree_entries(text: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for block in TOCTREE_BLOCK_RE.finditer(text):
        for line in block.group("entries").splitlines():
            title, path = parse_toctree_entry_line(line)
            if path:
                entries.append((title, path))
    return entries


def resolve_toctree_link(ctx: WikiContext, site: str, entry: str) -> str:
    entry = entry.replace("\\", "/").strip("/")
    if entry.startswith("docs/"):
        entry = entry[5:]
    if entry.endswith(".rst"):
        entry = entry[:-4]
    stem = entry.split("/")[-1]
    candidates = [
        vault_rel_path(vault_site_for(site), stem),
        vault_rel_path("common", stem),
        vault_rel_path("common", f"common-{stem}"),
        vault_rel_path(vault_site_for(site), entry),
    ]
    for rel in candidates:
        if (ctx.vault / rel).is_file():
            return rel.replace(".md", "")
    if f"common/{stem}" in ctx.doc_map:
        return ctx.doc_map[f"common/{stem}"].replace(".md", "")
    if stem in ctx.doc_map:
        return ctx.doc_map[stem].replace(".md", "")
    return f"{site}/{stem}"


def generate_site_indexes(ctx: WikiContext) -> None:
    for site in ctx.sites:
        index_rst = ctx.wiki_root / site / "source" / "index.rst"
        if not index_rst.is_file():
            index_rst = ctx.wiki_root / site / "source" / "docs" / "index.rst"
        if not index_rst.is_file():
            continue
        entries = parse_toctree_entries(index_rst.read_text(encoding="utf-8", errors="replace"))
        title = SITE_TITLES.get(site, site.title())
        lines = [
            "---",
            "source: ardupilot_wiki",
            f"site: {site}",
            "type: index",
            f"wiki_commit: {ctx.commit}",
            "---",
            "",
            f"# {title}",
            "",
            f"Official index: {web_url(site, 'index')}",
            "",
        ]
        for title, entry in entries:
            link = resolve_toctree_link(ctx, site, entry)
            if title:
                lines.append(f"- [[{link}|{title}]]")
            else:
                lines.append(f"- [[{link}]]")
        lines.append("")
        out = ctx.vault / site / "_index.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines), encoding="utf-8")


def generate_root_index(ctx: WikiContext) -> None:
    synced = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# ArduPilot Wiki（Obsidian 镜像）",
        "",
        f"> 同步自 [ardupilot_wiki](https://github.com/ArduPilot/ardupilot_wiki) @ `{ctx.commit}`",
        f"> 同步时间：{synced}",
        "",
        "许可：[[_meta/LICENSE|CC BY-SA 3.0]] · 元数据：[[_meta/source_info]]",
        "",
        "## 站点入口",
        "",
    ]
    for site in ctx.sites:
        title = SITE_TITLES.get(site, site.title())
        lines.append(f"- **{title}** — [[{site}/_index|{site} 索引]]")
    lines.extend(
        [
            "",
            "## Transwing 专题（本仓库）",
            "",
            "精确 TW_* 参数、混控、SITL 仍以 TRANSWING Git 仓库为准：",
            "",
            f"- 仓库路径：`{REPO_ROOT}`",
            "- 检索：`python tools/search_kb.py <关键词>`",
            "- 索引：[[knowledge-base README 需从 Obsidian 外链或本地打开 TRANSWING/knowledge-base/README.md]]",
            "",
            "## 同步命令",
            "",
            "```bash",
            "python tools/sync_ardupilot_wiki_obsidian.py --update",
            "```",
            "",
        ]
    )
    (ctx.vault / "00_索引.md").write_text("\n".join(lines), encoding="utf-8")


def write_params_phase2_note(vault: Path) -> None:
    path = vault / "_meta" / "PARAMS_PHASE2.md"
    path.write_text(
        """# Parameters 页（二期说明）

部分 **Parameters** 列表页由 `ardupilot_wiki` 的 `update.py` 在构建时从固件仓库拉取 XML **动态生成**，
不在静态 `.rst` 源文件中，因此本 Obsidian 镜像可能不含完整参数表。

**建议：**

- 日常查参：Mission Planner / QGroundControl 参数树，或固件附带的 `ParameterMetaData.xml`
- 在线对照：笔记 frontmatter 中的 `web_url` 打开官网
- 若需离线完整参数页：在 WSL/Docker 中本地运行 wiki 的 Sphinx 构建，再 html→md 导入（二期）

同步命令见 [[_meta/source_info]]。
""",
        encoding="utf-8",
    )


def write_source_info(ctx: WikiContext, manifest_dir: Path) -> None:
    text = f"""# Sync metadata

- wiki_commit: `{ctx.commit}`
- synced_at: {datetime.now(timezone.utc).isoformat()}
- sites: {", ".join(ctx.sites)}
- notes_converted: {ctx.converted}
- cache: `{ctx.wiki_root}`

```bash
python tools/sync_ardupilot_wiki_obsidian.py --update
python tools/sync_ardupilot_wiki_obsidian.py --relink-only
```
"""
    (ctx.vault / "_meta" / "source_info.md").write_text(text, encoding="utf-8")


def write_manifest(ctx: WikiContext, manifest_dir: Path) -> None:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    unresolved_path = manifest_dir / "unresolved_links.csv"
    with unresolved_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source_note", "link_type", "target"])
        for row in ctx.unresolved:
            writer.writerow(row)

    manifest = {
        "wiki_commit": ctx.commit,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "vault": str(ctx.vault),
        "sites": ctx.sites,
        "converted": ctx.converted,
        "skipped": ctx.skipped,
        "relinked": ctx.relinked,
        "unresolved_links": len(ctx.unresolved),
        "anchor_count": len(ctx.anchor_map),
    }
    (manifest_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def fallback_rst_markdown(rst_path: Path, site: str, stem: str) -> str:
    text = rst_path.read_text(encoding="utf-8", errors="replace").replace("\x00", "")
    title = stem.replace("-", " ").replace("_", " ").title()
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("..") and not line.startswith("="):
            if len(line) > 3 and not set(line) <= {"=", "-", "^", '"', "'"}:
                title = line.strip("=-^\"' ")
                break
    return (
        f"# {title}\n\n"
        f"> 此页 RST 自动转换失败，请打开 frontmatter 中的 `web_url` 查看官网原文。\n\n"
        f"```rst\n{text[:12000]}\n```\n"
    )


def convert_site(ctx: WikiContext, site: str, state: dict, incremental: bool, missing_only: bool = False) -> None:
    docs_dir = ctx.wiki_root / site / "source" / "docs"
    out_dir = ctx.vault / vault_site_for(site)
    out_dir.mkdir(parents=True, exist_ok=True)

    for rst in sorted(docs_dir.rglob("*.rst")):
        rel = rst.relative_to(ctx.wiki_root).as_posix()
        rel_to_docs = rst.relative_to(docs_dir)
        stem = rel_to_docs.with_suffix("").as_posix().replace("\\", "/")
        vault_rel = vault_rel_path(vault_site_for(site), stem)
        out_path = ctx.vault / vault_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

        digest = file_hash(rst)
        prev = state.get(rel, {})
        if missing_only and out_path.is_file():
            ctx.skipped += 1
            continue
        if incremental and prev.get("hash") == digest and out_path.is_file():
            ctx.skipped += 1
            continue

        try:
            body = rst_to_markdown(rst)
        except RuntimeError as exc:
            print(f"WARN convert failed: {rel}: {exc}", file=sys.stderr)
            body = fallback_rst_markdown(rst, site, stem)

        body = postprocess_body(ctx, body, vault_rel)
        doc = frontmatter(ctx, site, rel, stem) + body
        out_path.write_text(doc, encoding="utf-8")
        state[rel] = {"hash": digest, "vault": vault_rel}
        ctx.converted += 1


def relink_vault(ctx: WikiContext) -> None:
    for md in ctx.vault.rglob("*.md"):
        if "_meta" in md.parts or md.name in {"00_索引.md", "_index.md"}:
            continue
        vault_rel = md.relative_to(ctx.vault).as_posix()
        text = md.read_text(encoding="utf-8", errors="replace")
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                body = text[end + 3 :].lstrip("\n")
                fm = text[: end + 3]
            else:
                fm, body = "", text
        else:
            fm, body = "", text

        new_body = postprocess_body(ctx, body, vault_rel)
        if new_body != body:
            md.write_text(fm + "\n" + new_body if fm else new_body, encoding="utf-8")
            ctx.relinked += 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync ArduPilot wiki to Obsidian")
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--update", action="store_true", help="git pull and incremental convert")
    parser.add_argument("--relink-only", action="store_true", help="Only rebuild internal links")
    parser.add_argument("--indexes-only", action="store_true", help="Only regenerate site/root indexes")
    parser.add_argument("--missing-only", action="store_true", help="Convert only notes missing in vault")
    parser.add_argument("--skip-images", action="store_true")
    args = parser.parse_args()

    if not (args.cache / ".git").is_dir() and args.relink_only:
        print("Wiki cache missing; run full sync first.", file=sys.stderr)
        return 1

    commit = sync_wiki_repo(args.cache, update=(args.update or args.relink_only) and not args.relink_only)
    ctx = WikiContext(wiki_root=args.cache, vault=args.vault, commit=commit)
    ctx.sites = discover_sites(ctx.wiki_root)
    if not ctx.sites:
        print("No wiki sites found under cache.", file=sys.stderr)
        return 1

    ensure_vault_skeleton(ctx.vault)
    args.manifest_dir.mkdir(parents=True, exist_ok=True)
    scan_anchors_and_docs(ctx)
    state = load_state(args.manifest_dir)

    if args.relink_only:
        print("Relinking vault notes...")
        relink_vault(ctx)
    elif args.indexes_only:
        print("Regenerating indexes...")
        generate_site_indexes(ctx)
        generate_root_index(ctx)
    else:
        print(f"Converting {len(ctx.sites)} sites: {', '.join(ctx.sites)}")
        for site in ctx.sites:
            print(f"  [{site}]")
            convert_site(ctx, site, state, incremental=args.update, missing_only=args.missing_only)

        if not args.skip_images:
            print("Copying images...")
            img_count = copy_images(ctx.wiki_root, ctx.vault)
            print(f"  {img_count} image files")

        generate_site_indexes(ctx)
        generate_root_index(ctx)

    write_params_phase2_note(ctx.vault)
    write_source_info(ctx, args.manifest_dir)
    save_state(args.manifest_dir, state)
    write_manifest(ctx, args.manifest_dir)

    print(
        f"Done. converted={ctx.converted} skipped={ctx.skipped} "
        f"relinked={ctx.relinked} unresolved={len(ctx.unresolved)}"
    )
    print(f"Vault: {ctx.vault}")
    print(f"Manifest: {args.manifest_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
