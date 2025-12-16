from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from anki.collection import Collection  # type: ignore


def _cfg_get(cfg: Optional[Dict[str, Any]], path: list[str], default: Any) -> Any:
    cur: Any = cfg or {}
    for p in path:
        if not isinstance(cur, dict):
            return default
        if p not in cur:
            return default
        cur = cur[p]
    return cur


_RE_ANSWER_HR = re.compile(r'<hr[^>]*id=["\']answer["\'][^>]*>', re.I)


def _split_by_answer_hr(full_answer_html: str) -> Tuple[str, str, bool]:
    m = _RE_ANSWER_HR.search(full_answer_html or "")
    if not m:
        return full_answer_html, full_answer_html, False
    front = full_answer_html[: m.start()]
    back = full_answer_html[m.end() :]
    return front, back, True


def _strip_first_style_block(html: str) -> str:
    return re.sub(r"<style.*?</style>", "", html or "", count=1, flags=re.S | re.I)


def _doc_head(cfg: Optional[Dict[str, Any]] = None) -> str:
    img_w = int(_cfg_get(cfg, ["04_images", "img_max_width_px"], 800) or 800)
    img_h = int(_cfg_get(cfg, ["04_images", "img_max_height_px"], 400) or 400)
    pdf_font = int(_cfg_get(cfg, ["02_export", "pdf_font_size_px"], 16) or 16)

    pdf_layout = str(_cfg_get(cfg, ["02_export", "pdf_layout"], "single") or "single").lower().strip()
    if pdf_layout not in {"single", "two_column"}:
        pdf_layout = "single"

    # PDF向け：print時だけ二段組などを適用（QWebEnginePage.printToPdf は print CSS が効く）
    if pdf_layout == "two_column":
        print_css = f"""
@media print {{
  body {{
    font-size: {pdf_font}px;
  }}
  .cards {{
    column-count: 2;
    column-gap: 16px;
  }}
  .card {{
    break-inside: avoid;
    page-break-inside: avoid;
  }}
}}
"""
    else:
        print_css = f"""
@media print {{
  body {{
    font-size: {pdf_font}px;
  }}
  .card {{
    break-inside: avoid;
    page-break-inside: avoid;
  }}
}}
"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>Anki Export</title>
  <style>
.card {{
    color: #222222;
    background-color: #ffffff;
    line-height: 2;
    font-family: "Yu Gothic UI", "Yu Gothic", "Meiryo",
               "Hiragino Sans", "Noto Sans JP", sans-serif;
    font-size: 18px;
    text-align: left;
    padding: 20px;
    border-radius: 14px;
    margin-bottom: 18px;
    box-shadow: 0 0 10px rgba(0,0,0,0.08);
}}
.content {{
    width: 95%;
    margin: auto;
}}
img {{
    max-width: {img_w}px;
    max-height: {img_h}px;
}}
{print_css}
  </style>
</head>
<body>
<div class="cards">
"""


DOC_FOOT = """
</div>
</body>
</html>
"""


def build_export_html(col: Collection, card_ids, cfg: Optional[Dict[str, Any]] = None) -> str:
    mode = str(_cfg_get(cfg, ["02_export", "export_mode"], "back") or "back").lower().strip()
    if mode not in {"front", "back", "both"}:
        mode = "back"

    cards_html: list[str] = []

    for cid in card_ids:
        card = col.get_card(cid)
        note = card.note()

        model = note.note_type() if hasattr(note, "note_type") else note.model()
        css = model.get("css", "")

        full_answer_html = card.answer()
        front_html, back_html, _found = _split_by_answer_hr(full_answer_html)

        if mode == "front":
            body_html = front_html
        elif mode == "back":
            body_html = back_html
        else:
            body_html = full_answer_html

        body_html = _strip_first_style_block(body_html)

        cards_html.append(
            f"""
<div class="card">
  <style>
{css}
  </style>
  <div class="content">
{body_html}
  </div>
</div>
"""
        )

    return _doc_head(cfg) + "\n".join(cards_html) + DOC_FOOT


def export_cards_html(col: Collection, card_ids, output_file: Path, cfg: Optional[Dict[str, Any]] = None) -> str:
    html = build_export_html(col, card_ids, cfg)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html, encoding="utf-8")

    if bool(_cfg_get(cfg, ["02_export", "copy_media_files"], True)):
        media_dir = Path(col.media.dir())
        _copy_images_from_html(html, media_dir, output_file.parent)

    return html


def _copy_images_from_html(html: str, media_dir: Path, out_dir: Path) -> None:
    image_srcs = set(re.findall(r'src="([^"]+)"', html or ""))
    if not image_srcs or not media_dir.exists():
        return

    for src_val in image_srcs:
        if not src_val:
            continue
        if src_val.startswith("data:"):
            continue
        if "://" in src_val or src_val.startswith("file:"):
            continue

        name = src_val.split("?", 1)[0].split("#", 1)[0].strip()
        if not name:
            continue

        src = media_dir / name
        dst = out_dir / name
        if src.exists():
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass
