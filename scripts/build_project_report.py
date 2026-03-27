from __future__ import annotations

import datetime as _dt
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "docs" / "project_report"


@dataclass(frozen=True)
class ReportConfig:
    title: str
    subtitle: str
    author: str
    version: str
    language: str
    frontend_path: str | None
    ms_path: Path
    pdf_path: Path
    sections: list[Path]


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _load_config() -> ReportConfig:
    cfg_path = REPORT_DIR / "config.yaml"
    raw = yaml.safe_load(_read_text(cfg_path)) or {}

    output = raw.get("output") or {}
    sections = [ROOT / p for p in (raw.get("sections") or [])]
    return ReportConfig(
        title=str(raw.get("title") or "Project Report"),
        subtitle=str(raw.get("subtitle") or ""),
        author=str(raw.get("author") or ""),
        version=str(raw.get("version") or "1.0"),
        language=str(raw.get("language") or "en"),
        frontend_path=str(raw.get("frontend_path")) if raw.get("frontend_path") else None,
        ms_path=ROOT / str(output.get("ms_path") or "docs/project_report/dist/project_report.ms"),
        pdf_path=ROOT / str(output.get("pdf_path") or "docs/project_report/dist/project_report.pdf"),
        sections=sections,
    )


def _indent_lines(text: str, prefix: str) -> str:
    return "\n".join(prefix + line if line.strip() else line for line in text.splitlines())


def _safe_bullet(text: str) -> str:
    # Avoid a line starting with '.' being interpreted as a roff request.
    if text.startswith("."):
        return r"\&" + text
    return text


def _inline_format(md: str) -> str:
    # Very small subset: `code`, **bold**, *italic*.
    # Order matters to reduce conflicts.
    md = re.sub(r"`([^`]+)`", r"\\f[CR]\1\\f[]", md)
    md = re.sub(r"\*\*([^*]+)\*\*", r"\\f[B]\1\\f[]", md)
    md = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\\f[I]\1\\f[]", md)
    return md


def _extract_backend_tree() -> str:
    # Short tree-like listing (depth 2) to keep the PDF readable.
    lines: list[str] = []
    base = ROOT
    for p in sorted(base.iterdir()):
        if p.name in {".git", "__pycache__", ".venv"}:
            continue
        if p.is_dir():
            lines.append(f"- {p.name}/")
            for child in sorted(p.iterdir()):
                if child.name in {".git", "__pycache__"}:
                    continue
                if child.is_dir():
                    lines.append(f"  - {child.name}/")
                else:
                    lines.append(f"  - {child.name}")
        else:
            lines.append(f"- {p.name}")
    return "\n".join(lines)


def _extract_backend_overview() -> str:
    readme = ROOT / "README.md"
    if not readme.exists():
        return ""
    text = _read_text(readme).strip()
    # Keep just the first ~20 lines.
    return "\n".join(text.splitlines()[:20]).strip()


def _extract_env_var_names() -> str:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return "- (no .env found)"

    names: list[str] = []
    for line in _read_text(env_path).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if re.fullmatch(r"[A-Z0-9_]+", key):
            names.append(key)

    names = sorted(set(names))
    if not names:
        return "- (no variables found)"
    return "\n".join(f"- {n}" for n in names)


def _extract_fastapi_routes() -> str:
    routers_dir = ROOT / "app" / "routers"
    if not routers_dir.exists():
        return "- (routers directory not found)"

    route_re = re.compile(
        r"@router\.(get|post|put|delete|patch|options|head)\(\s*['\"]([^'\"]+)['\"]",
        re.IGNORECASE,
    )
    prefix_re = re.compile(r"APIRouter\([^)]*prefix\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)

    routes: list[str] = []
    for path in sorted(routers_dir.glob("*.py")):
        src = _read_text(path)
        prefix = ""
        m = prefix_re.search(src)
        if m:
            prefix = m.group(1)

        for m in route_re.finditer(src):
            method = m.group(1).upper()
            route_path = m.group(2)
            full = (prefix.rstrip("/") + "/" + route_path.lstrip("/")).rstrip("/") or "/"
            routes.append(f"- {method} {full} ({path.name})")

    routes = sorted(set(routes))
    if not routes:
        return "- (no routes found via decorator scan)"
    return "\n".join(routes)


def _extract_backend_modules() -> str:
    items: list[str] = []
    app_dir = ROOT / "app"
    if not app_dir.exists():
        return "- (app/ not found)"

    for name in ["core", "db", "models", "routers", "schemas", "services"]:
        p = app_dir / name
        if p.exists():
            items.append(f"- app/{name}/")

    main = app_dir / "main.py"
    if main.exists():
        items.append("- app/main.py (entrée FastAPI)")

    if not items:
        return "- (no modules found)"
    return "\n".join(items)


def _extract_backend_models() -> str:
    models_dir = ROOT / "app" / "models"
    if not models_dir.exists():
        return "- (models directory not found)"

    class_re = re.compile(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)
    items: list[str] = []
    for path in sorted(models_dir.glob("*.py")):
        if path.name.startswith("__"):
            continue
        src = _read_text(path)
        classes = class_re.findall(src)
        if classes:
            for cls in classes[:5]:
                items.append(f"- {cls} ({path.name})")
        else:
            items.append(f"- {path.stem} ({path.name})")

    items = sorted(set(items))
    if not items:
        return "- (no models found)"
    return "\n".join(items)


def _extract_frontend_tree(frontend_path: str | None) -> str:
    if not frontend_path:
        return "- (frontend_path not configured)"
    base = Path(frontend_path)
    if not base.exists():
        return f"- (frontend_path not found: {frontend_path})"

    keep_files = {"pubspec.yaml", "README.md", "analysis_options.yaml"}
    lines: list[str] = [f"- {base.name}/"]
    for p in sorted(base.iterdir()):
        if p.name in {".git", ".dart_tool", "build", ".idea"}:
            continue
        if p.is_dir():
            lines.append(f"  - {p.name}/")
        elif p.name in keep_files:
            lines.append(f"  - {p.name}")
    return "\n".join(lines)


def _extract_frontend_tech(frontend_path: str | None) -> str:
    if not frontend_path:
        return "- (frontend_path not configured)"
    base = Path(frontend_path)
    pubspec = base / "pubspec.yaml"
    if not pubspec.exists():
        return "- Flutter (pubspec.yaml non trouvé)"

    deps: list[str] = []
    in_deps = False
    for line in _read_text(pubspec).splitlines():
        if re.match(r"^dependencies\\s*:\\s*$", line):
            in_deps = True
            continue
        if in_deps and re.match(r"^[A-Za-z0-9_]+\\s*:\\s*$", line):
            deps.append(line.split(":", 1)[0].strip())
        if in_deps and re.match(r"^dev_dependencies\\s*:\\s*$", line):
            break

    deps = deps[:20]
    out = ["- Flutter / Dart"]
    if deps:
        out.append("- Dépendances clés (extrait) : " + ", ".join(deps))
    return "\n".join(out)


def _apply_placeholders(md: str, context: dict[str, str]) -> str:
    for key, value in context.items():
        md = md.replace("{{" + key + "}}", value)
    return md


def _md_to_ms(md: str, assets_dir: Path) -> tuple[str, list[tuple[int, str, int]]]:
    """
    Converts a small Markdown subset to groff ms content.

    Returns:
      (ms_body, toc_entries) where toc_entries is a list of (level, title, page_hint)
      page_hint is unused (kept for future enhancement).
    """

    lines = md.splitlines()
    out: list[str] = []
    toc: list[tuple[int, str, int]] = []

    in_code = False
    code_lines: list[str] = []
    fig_no = 0

    def flush_paragraph(par: list[str]) -> None:
        if not par:
            return
        text = " ".join(s.strip() for s in par).strip()
        if not text:
            return
        out.append(_safe_bullet(_inline_format(text)))
        out.append("")
        par.clear()

    paragraph: list[str] = []

    img_re = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")

    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")

        if line.strip().startswith("```"):
            if in_code:
                # end block
                out.append(".DS I")
                out.append(".ft CR")
                out.append(".ps 9")
                out.append(".vs 11")
                for cl in code_lines:
                    out.append(_safe_bullet(cl))
                out.append(".ft")
                out.append(".DE")
                out.append("")
                code_lines = []
                in_code = False
            else:
                flush_paragraph(paragraph)
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        m = img_re.match(line.strip())
        if m:
            flush_paragraph(paragraph)
            caption = m.group(1).strip() or "Capture d’écran"
            rel_path = m.group(2).strip()
            img_path = (REPORT_DIR / rel_path).resolve() if rel_path.startswith("assets/") else (assets_dir / rel_path)

            fig_no += 1
            out.append(".sp 0.2i")
            out.append(f".PDFPIC -C {img_path} 2.6i")
            out.append(".sp 0.1i")
            out.append(".ce 1")
            out.append(_safe_bullet(_inline_format(f"Figure {fig_no} — {caption}")))
            out.append(".ce 0")
            out.append(".sp 0.2i")
            out.append("")
            i += 1
            continue

        if not line.strip():
            flush_paragraph(paragraph)
            i += 1
            continue

        if line.lstrip().startswith("#"):
            flush_paragraph(paragraph)
            hashes = len(line) - len(line.lstrip("#"))
            level = max(1, min(3, hashes))
            title = line.strip("#").strip()
            title = re.sub(r"\s+", " ", title)
            toc.append((level, title, 0))
            out.append(f".NH {level}")
            out.append(_safe_bullet(_inline_format(title)))
            out.append("")
            i += 1
            continue

        if line.lstrip().startswith("- "):
            flush_paragraph(paragraph)
            item = line.split("- ", 1)[1].strip()
            out.append(r".IP \(bu 2")
            out.append(_safe_bullet(_inline_format(item)))
            out.append("")
            i += 1
            continue

        if line.lstrip().startswith("> "):
            flush_paragraph(paragraph)
            out.append(".RS")
            out.append(".I")
            out.append(_safe_bullet(_inline_format(line.lstrip()[2:].strip())))
            out.append(".R")
            out.append(".RE")
            out.append("")
            i += 1
            continue

        paragraph.append(line)
        i += 1

    flush_paragraph(paragraph)
    return "\n".join(out).rstrip() + "\n", toc


def _toc_to_ms(toc: list[tuple[int, str, int]], title: str) -> str:
    out: list[str] = []
    out.append(".NH 1")
    out.append(title)
    out.append("")
    out.append("Cette table des matières est générée à partir des titres du document.")
    out.append("")
    out.append(".nf")
    for level, t, _ in toc:
        if level == 1:
            out.append(_inline_format(f"- {t}"))
        elif level == 2:
            out.append(_inline_format(f"  - {t}"))
        else:
            out.append(_inline_format(f"    - {t}"))
    out.append(".fi")
    out.append("")
    return "\n".join(out).rstrip() + "\n"


def _build_ms(config: ReportConfig) -> str:
    today = _dt.date.today().isoformat()

    context = {
        "BACKEND_README_OVERVIEW": _extract_backend_overview(),
        "BACKEND_ENV_VARS": _extract_env_var_names(),
        "BACKEND_ROUTES": _extract_fastapi_routes(),
        "BACKEND_MODULES": _extract_backend_modules(),
        "BACKEND_MODELS": _extract_backend_models(),
        "BACKEND_TREE": _extract_backend_tree(),
        "FRONTEND_TECH": _extract_frontend_tech(config.frontend_path),
        "FRONTEND_TREE": _extract_frontend_tree(config.frontend_path),
    }

    assets_dir = REPORT_DIR / "assets"

    all_body: list[str] = []
    toc_entries: list[tuple[int, str, int]] = []

    for section_path in config.sections:
        md = _read_text(section_path)
        md = _apply_placeholders(md, context)
        ms_body, toc = _md_to_ms(md, assets_dir=assets_dir)
        all_body.append(ms_body)
        toc_entries.extend(toc)

    toc_title = "Table des matières" if config.language.lower().startswith("fr") else "Table of Contents"

    preamble = f"""\\.\\\" Auto-generated. Edit Markdown in docs/project_report/sections/.
.po 1i
.ll 6.25i
.nr HM 1.0i
.nr FM 0.9i
.fam H
.ps 11
.vs 14
.pn 1
.ds REPORT_TITLE {config.title}
.ds REPORT_SUBTITLE {config.subtitle}
.ds REPORT_AUTHOR {config.author}
.ds REPORT_VERSION {config.version}
.ds REPORT_DATE {today}
.ds CF \\s[9]\\*[REPORT_TITLE]\\s[0]
.ds LF
.ds RF
.OF '\\\\*[LF]'\\\\*[CF]'\\\\*[RF]'
.EF '\\\\*[LF]'\\\\*[CF]'\\\\*[RF]'

.\" Cover
.sp 1.3i
.ce 1
\\f[B]\\s[28]\\*[REPORT_TITLE]\\s[0]\\f[]
.sp 0.15i
.ce 1
\\s[13]\\*[REPORT_SUBTITLE]\\s[0]
.sp 0.6i
.ce 1
\\s[10]Version \\*[REPORT_VERSION]\\s[0]
.sp 0.2i
.ce 1
\\s[10]\\*[REPORT_AUTHOR]\\s[0]
.sp 0.2i
.ce 1
\\s[10]\\*[REPORT_DATE]\\s[0]
.ce 0
.bp
"""

    toc_ms = _toc_to_ms(toc_entries, toc_title)

    return preamble + toc_ms + "\n.bp\n\n" + "\n".join(all_body)


def _write_outputs(config: ReportConfig, ms: str) -> None:
    config.ms_path.parent.mkdir(parents=True, exist_ok=True)
    config.pdf_path.parent.mkdir(parents=True, exist_ok=True)
    config.ms_path.write_text(ms, encoding="utf-8")


def _build_pdf(config: ReportConfig) -> None:
    # pdfpic requires unsafe mode (-U)
    cmd = [
        "groff",
        "-U",
        "-Kutf8",
        "-Tpdf",
        "-ms",
        "-mpdfpic",
        str(config.ms_path),
    ]
    pdf_bytes = subprocess.check_output(cmd)
    config.pdf_path.write_bytes(pdf_bytes)


def main() -> None:
    config = _load_config()
    ms = _build_ms(config)
    _write_outputs(config, ms)
    _build_pdf(config)

    rel_pdf = config.pdf_path.relative_to(ROOT)
    print(f"OK: generated {rel_pdf}")


if __name__ == "__main__":
    main()
