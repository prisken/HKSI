#!/usr/bin/env python3
"""Extract HKSI study manual into versioned JSON + figure PNGs.

Improves readability:
- numbered paragraphs (1.1) as subheads
- lettered / bullet lists
- joins broken CJK lines
- renders vector diagrams as PNG and inserts figure blocks
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF = Path("/Users/priskenlo/Downloads/896219724-HKSI-Study-Manual-L01-Chi.pdf")
OUT_ROOT = ROOT / "public" / "data" / "manual"

VERSION_ID = "v2.8-2016-08"
META = {
    "versionId": VERSION_ID,
    "edition": "第二版",
    "versionLabel": "2.8",
    "versionFull": "第 2.8 版",
    "firstPublished": "2011-04",
    "firstPublishedLabel": "二零一一年四月",
    "updatedThrough": "2016-08",
    "updatedThroughLabel": "二零一六年八月",
    "publisher": "香港證券及投資學會",
    "paper": "試卷一：基本證券及期貨規例",
    "isbn": "978-988-97139-6-9",
    "sourceFile": PDF.name,
    "notes": [
        "內容摘自 HKSI 溫習手冊電子版；圖表由原 PDF 向量頁面截取。",
        "考試題目以學會當時有效之溫習手冊及更新文件為準。",
        "本應用並非 HKSI 官方產品。",
    ],
}

CHAPTER_RANGES = {
    1: (18, 38),
    2: (42, 59),
    3: (62, 87),
    4: (90, 129),
    5: (132, 166),
    6: (170, 198),
    7: (202, 227),
    8: (230, 258),
    9: (262, 278),
}

CHAPTER_TITLES = {
    1: "香港金融業監管概覽",
    2: "相關香港法例及新《公司條例》的原則",
    3: "《證券及期貨條例》",
    4: "發牌及註冊與附屬法例",
    5: "業務操守與客戶關係",
    6: "業務運作與常規",
    7: "在香港交易所的參與",
    8: "企業融資及證監會的認可產品",
    9: "市場失當行為及不當交易行為",
}

TOC_PAGES = {1: 17, 2: 41, 3: 61, 4: 89, 5: 131, 6: 169, 7: 201, 8: 229, 9: 261}
SPECIAL_HEADERS = ["本章概覽", "學習重點", "本章摘要", "要點"]
CAPTION_RE = re.compile(r"^圖\s*(\d+)\s*[：:︰]\s*(.*)$")
SUBHEAD_RE = re.compile(r"^(\d+\.\d+(?:\.\d+)?)\s+(.+)$")
LETTER_LI_RE = re.compile(r"^\(([a-z]|[ivx]+)\)\s*(.*)$", re.I)


def clean_line(s: str) -> str:
    s = s.replace("\u00a0", " ").replace("\ufeff", "")
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s


def clean_page_text(text: str) -> List[str]:
    lines = []
    for raw in text.splitlines():
        line = clean_line(raw)
        if not line:
            continue
        if re.match(r"^試卷一\s*2\.8\s*版", line):
            continue
        if "©香港證券及投資學會" in line or "© 香港證券及投資學會" in line:
            continue
        if line in {"「空白頁」", "空白頁"}:
            continue
        lines.append(line)
    return lines


def parse_toc_sections(toc_text: str) -> List[Dict[str, str]]:
    raw_lines = [clean_line(x) for x in toc_text.splitlines() if clean_line(x)]
    merged: List[str] = []
    for line in raw_lines:
        if (
            merged
            and not re.match(r"^(\d{1,2})\s+", line)
            and not any(line.startswith(sp) for sp in SPECIAL_HEADERS)
            and not line.startswith("第")
            and not line.startswith("目錄")
            and not re.match(r"^一般原則", line)
        ):
            prev = merged[-1]
            if re.match(r"^\d{1,2}\s+\S", prev) and (
                not re.search(r"\s\d+\s*$", prev)
                or prev.rstrip().endswith(("監控", "規", "的", "及", "與", "內部"))
            ):
                merged[-1] = re.sub(r"\s+\d+\s*$", "", prev) + line
                continue
        merged.append(line)

    sections: List[Dict[str, str]] = []
    expected = 1
    for line in merged:
        matched_special = False
        for sp in SPECIAL_HEADERS:
            if line.startswith(sp):
                sid = {
                    "本章概覽": "overview",
                    "學習重點": "objectives",
                    "本章摘要": "summary",
                    "要點": "keypoints",
                }[sp]
                if not any(s["id"] == sid for s in sections):
                    sections.append({"id": sid, "title": sp})
                matched_special = True
                break
        if matched_special:
            continue
        m = re.match(r"^(\d{1,2})\s+(.+?)(?:\s+(\d+))?\s*$", line)
        if not m:
            continue
        num = int(m.group(1))
        title = clean_line(re.sub(r"\s+\d+$", "", m.group(2)))
        if num != expected or len(title) < 2:
            continue
        sections.append({"id": str(num), "title": title})
        expected = num + 1
    return sections


def build_header_matcher(toc_sections: List[Dict[str, str]]):
    by_num = {s["id"]: s["title"] for s in toc_sections if s["id"].isdigit()}

    def norm(s: str) -> str:
        s = s.replace("“", "").replace("”", "").replace('"', "").replace("'", "")
        s = s.replace("（", "(").replace("）", ")")
        return re.sub(r"\s+", "", s)

    def match(line: str) -> Optional[Tuple[str, str]]:
        for sp in SPECIAL_HEADERS:
            if line == sp:
                sid = {
                    "本章概覽": "overview",
                    "學習重點": "objectives",
                    "本章摘要": "summary",
                    "要點": "keypoints",
                }[sp]
                return sid, sp
        m = re.match(r"^(\d{1,2})\s+(.+)$", line)
        if not m:
            return None
        num, rest = m.group(1), clean_line(m.group(2))
        if num not in by_num:
            return None
        title = by_num[num]
        nr, nt = norm(rest), norm(title)
        if nr == nt:
            return num, f"{num} {title}"
        if len(nt) >= 6 and (
            nr.startswith(nt[: min(12, len(nt))]) or nt.startswith(nr[: min(12, len(nr))])
        ):
            if len(nr) >= max(4, int(len(nt) * 0.45)):
                return num, f"{num} {title}"
        return None

    return match


def join_cjk(parts: List[str]) -> str:
    if not parts:
        return ""
    out = parts[0]
    for p in parts[1:]:
        if re.search(r"[\u4e00-\u9fffA-Za-z0-9%）)%》」]$", out) and re.match(
            r"^[\u4e00-\u9fff（(《「]", p
        ):
            out += p
        else:
            out += " " + p
    return re.sub(r"\s+", " ", out).strip()


def lines_to_blocks(lines: List[str], figures_by_caption: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    buf: List[str] = []

    def flush() -> None:
        nonlocal buf
        parts = [p for p in buf if p.strip()]
        buf = []
        if not parts:
            return
        text = join_cjk(parts)
        if text:
            blocks.append({"type": "p", "text": text})

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Figure caption (only emit when we have a rendered PNG)
        strict = CAPTION_RE.match(line) or re.match(r"^圖\s*(\d+)\s*[：:︰]\s*(.*)$", line)
        if strict:
            flush()
            num = strict.group(1)
            caption = clean_line(line)
            key = f"圖{num}"
            fig = figures_by_caption.get(key) or figures_by_caption.get(f"圖 {num}")
            if fig and fig.get("src"):
                blocks.append(
                    {
                        "type": "figure",
                        "caption": fig.get("caption") or caption,
                        "figureId": key,
                        "kind": "figure",
                        "src": fig["src"],
                        "alt": fig.get("alt") or caption,
                    }
                )
            else:
                # keep caption as text so readers still see the label
                blocks.append({"type": "p", "text": caption})
            i += 1
            continue

        # Paragraph numbers like 1.1 / 2.3 — keep as body with num badge, not giant headings
        sm = SUBHEAD_RE.match(line)
        if sm:
            rest = clean_line(sm.group(2))
            # True mini-title: short, no sentence end
            is_title = (
                len(rest) <= 28
                and "。" not in rest
                and not rest.endswith(("：", ":", "，", ","))
                and re.search(r"[\u4e00-\u9fff]", rest)
            )
            flush()
            if is_title:
                blocks.append({"type": "h3", "text": f"{sm.group(1)} {rest}"})
            else:
                # gather rest of paragraph
                cont = [rest]
                j = i + 1
                while j < len(lines):
                    nxt = lines[j].strip()
                    if not nxt:
                        break
                    if (
                        SUBHEAD_RE.match(nxt)
                        or LETTER_LI_RE.match(nxt)
                        or nxt[0] in "•"
                        or CAPTION_RE.match(nxt)
                        or re.match(r"^圖\s*\d+\s*[：:︰]", nxt)
                        or re.match(r"^表\s*\d+", nxt)
                    ):
                        break
                    cont.append(nxt)
                    j += 1
                    if nxt.endswith(("。", "；")) and len(join_cjk(cont)) > 40:
                        break
                blocks.append({"type": "p", "num": sm.group(1), "text": join_cjk(cont)})
                i = j
                continue

        # Table caption 表1 — only with colon or exact short label
        tm = re.match(r"^表\s*(\d+)\s*[：:︰]\s*(.+)$", line)
        tm_bare = re.fullmatch(r"表\s*(\d+)", line)
        if tm or tm_bare:
            flush()
            if tm:
                num = tm.group(1)
                caption = clean_line(line)
            else:
                num = tm_bare.group(1)
                caption = f"表 {num}"
                j = i + 1
                if j < len(lines) and len(lines[j]) < 40 and "。" not in lines[j]:
                    caption = f"表 {num}：{clean_line(lines[j])}"
                    i = j
            key = f"表{num}"
            fig = figures_by_caption.get(key) or figures_by_caption.get(f"表 {num}")
            if fig and fig.get("src"):
                blocks.append(
                    {
                        "type": "figure",
                        "caption": fig.get("caption") or caption,
                        "figureId": key,
                        "kind": "table",
                        "src": fig["src"],
                        "alt": fig.get("alt") or caption,
                    }
                )
            i += 1
            continue

        # bullets
        if line[0] in "•" or line.startswith("•"):
            flush()
            text = clean_line(re.sub(r"^[•]\s*", "", line))
            # join following continuation lines that don't start a new item
            j = i + 1
            cont = [text]
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt:
                    break
                if (
                    nxt[0] in "•"
                    or LETTER_LI_RE.match(nxt)
                    or SUBHEAD_RE.match(nxt)
                    or CAPTION_RE.match(nxt)
                    or re.match(r"^\d{1,2}\s+\S", nxt)
                ):
                    break
                if re.match(r"^\([a-z]\)", nxt):
                    break
                cont.append(nxt)
                j += 1
            blocks.append({"type": "li", "text": join_cjk(cont)})
            i = j
            continue

        # (a) (b) list
        lm = LETTER_LI_RE.match(line)
        if lm:
            flush()
            cont = [line]
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt or LETTER_LI_RE.match(nxt) or nxt[0] in "•" or SUBHEAD_RE.match(nxt):
                    break
                if CAPTION_RE.match(nxt) or re.match(r"^圖\s*\d+\s*[：:︰]", nxt):
                    break
                cont.append(nxt)
                j += 1
            blocks.append({"type": "li", "text": join_cjk(cont)})
            i = j
            continue

        buf.append(line)
        if line.endswith(("。", "；", "？", "!", "！")) and len(join_cjk(buf)) > 35:
            flush()
        i += 1
    flush()

    # Post-pass: merge orphan short paragraphs that are clearly list continuations
    return blocks



def count_grid_lines(page: fitz.Page) -> Tuple[int, int, List[fitz.Rect]]:
    """Return (hlines, vlines, segment rects) for table/diagram detection.

    Ignores header/footer rule lines so table clips stay tight.
    """
    page_rect = page.rect
    top_cut = page_rect.y0 + 70
    bot_cut = page_rect.y1 - 55
    h_segs: List[fitz.Rect] = []
    v_segs: List[fitz.Rect] = []
    for d in page.get_drawings():
        for item in d.get("items", []):
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 1.5 and abs(p1.x - p2.x) > 30:
                    y = (p1.y + p2.y) / 2
                    if top_cut <= y <= bot_cut:
                        h_segs.append(fitz.Rect(min(p1.x, p2.x), y - 1, max(p1.x, p2.x), y + 1))
                elif abs(p1.x - p2.x) < 1.5 and abs(p1.y - p2.y) > 30:
                    # vertical: require overlap with content band
                    y0, y1 = min(p1.y, p2.y), max(p1.y, p2.y)
                    if y1 > top_cut and y0 < bot_cut:
                        v_segs.append(
                            fitz.Rect(p1.x - 1, max(y0, top_cut), p1.x + 1, min(y1, bot_cut))
                        )
            elif item[0] == "re":
                r = item[1]
                cy = (r.y0 + r.y1) / 2
                if r.width > 40 and r.height < 4 and top_cut <= cy <= bot_cut:
                    h_segs.append(fitz.Rect(r))
                elif r.height > 40 and r.width < 4 and r.y1 > top_cut and r.y0 < bot_cut:
                    v_segs.append(
                        fitz.Rect(r.x0, max(r.y0, top_cut), r.x1, min(r.y1, bot_cut))
                    )

    # Keep the densest horizontal-line cluster (true table body), drop stray rules
    if len(h_segs) >= 3:
        h_segs = sorted(h_segs, key=lambda r: r.y0)
        best: List[fitz.Rect] = []
        cur: List[fitz.Rect] = [h_segs[0]]
        for seg in h_segs[1:]:
            # Tall table rows (multi-line cells) can span ~70pt between rules
            if seg.y0 - cur[-1].y0 <= 85:
                cur.append(seg)
            else:
                if len(cur) > len(best):
                    best = cur
                cur = [seg]
        if len(cur) > len(best):
            best = cur
        if len(best) >= 3:
            y0 = best[0].y0 - 4
            y1 = best[-1].y1 + 4
            h_segs = best
            v_segs = [v for v in v_segs if v.y1 >= y0 and v.y0 <= y1]

    rects = h_segs + v_segs
    return len(h_segs), len(v_segs), rects


def clip_for_visual(page: fitz.Page, kind: str, caption: str) -> fitz.Rect:
    """Tight clip around diagram/table grid (+ caption), not whole page body."""
    page_rect = page.rect
    hlines, vlines, grid_rects = count_grid_lines(page)
    drawings = page.get_drawings()
    draw_rects = [fitz.Rect(d["rect"]) for d in drawings if d.get("rect")]
    # Ignore header/footer drawing noise for diagrams too
    draw_rects = [
        r
        for r in draw_rects
        if r.y1 > page_rect.y0 + 70 and r.y0 < page_rect.y1 - 55 and r.height > 2
    ]

    caption_rects: List[fitz.Rect] = []
    caption_keys = ["圖", "表", "概要", "現行安排", "產品類別", "牌照涵蓋", "開市前時段"]
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            lt = "".join(span.get("text", "") for span in line.get("spans", []))
            s = lt.strip()
            if any(k in s for k in caption_keys) and len(s) < 80:
                caption_rects.append(fitz.Rect(line["bbox"]))

    if kind == "表" and grid_rects and hlines >= 3:
        union = grid_rects[0]
        for r in grid_rects[1:]:
            union |= r
        # only captions immediately above the grid
        for r in caption_rects:
            if union.y0 - 90 <= r.y0 <= union.y0 + 20:
                union |= r
        pad_x, pad_y_top, pad_y_bot = 16, 22, 12
        clip = fitz.Rect(
            max(page_rect.x0 + 28, union.x0 - pad_x),
            max(page_rect.y0 + 42, union.y0 - pad_y_top),
            min(page_rect.x1 - 28, union.x1 + pad_x),
            min(page_rect.y1 - 42, union.y1 + pad_y_bot),
        )
        return clip

    rects = draw_rects or grid_rects
    if not rects:
        return fitz.Rect(page_rect.x0 + 40, page_rect.y0 + 70, page_rect.x1 - 40, page_rect.y1 - 60)
    union = rects[0]
    for r in rects[1:]:
        union |= r
    for r in caption_rects:
        if abs(r.y0 - union.y0) < 180 or abs(r.y1 - union.y1) < 80:
            union |= r
    return fitz.Rect(
        max(page_rect.x0 + 28, union.x0 - 14),
        max(page_rect.y0 + 42, union.y0 - 18),
        min(page_rect.x1 - 28, union.x1 + 14),
        min(page_rect.y1 - 42, union.y1 + 14),
    )


def extract_figures(doc: fitz.Document, version_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Render known diagram/table pages and caption-matched 圖N pages."""
    fig_dir = version_dir / "figures"
    # clean old noisy exports
    if fig_dir.exists():
        for old in fig_dir.glob("*.png"):
            old.unlink()
    fig_dir.mkdir(parents=True, exist_ok=True)
    figures: Dict[str, Dict[str, Any]] = {}
    scale = 2.2

    def chapter_of(page_index: int) -> int:
        for ch, (a, b) in CHAPTER_RANGES.items():
            if a <= page_index <= b:
                return ch
        return 0

    # Curated pages: (0-based page index, kind, num, caption)
    curated = [
        (22, "圖", "1", "圖 1：政府及財經事務"),
        (23, "圖", "2", "圖 2：財經事務科架構"),
        (29, "圖", "3", "圖 3：證監會截至 2016 年 7 月的組織架構圖"),
        (33, "圖", "4", "圖 4：證監會及其同級監管機構"),
        (46, "圖", "1", "圖 1：法院架構"),
        (94, "表", "A", "受規管活動牌照涵蓋範圍概要"),
        (125, "表", "1", "表 1：場外衍生工具指明產品類別與類型"),
        (209, "表", "B", "聯交所交易時間（現行安排）"),
    ]

    curated_pages = {c[0] for c in curated}

    # Auto-include 圖N： captions
    for pi in range(doc.page_count):
        if pi in curated_pages:
            continue
        text = doc[pi].get_text() or ""
        m = re.search(r"(圖)\s*(\d+)\s*[：:︰]\s*([^\n]{0,60})", text)
        if m and chapter_of(pi):
            curated.append((pi, m.group(1), m.group(2), clean_line(m.group(0))))
            curated_pages.add(pi)

    # Auto-include 表N captions / bare 表N
    for pi in range(doc.page_count):
        if pi in curated_pages:
            continue
        text = doc[pi].get_text() or ""
        m = re.search(r"(表)\s*(\d+)\s*[：:︰]\s*([^\n]{0,60})", text)
        if not m:
            m = re.search(r"(?:^|\n)\s*(表)\s*(\d+)\s*(?:\n|$)", text)
        if m and chapter_of(pi):
            cap = clean_line(m.group(0))
            if len(cap) < 8:
                # grab following short title line if present
                after = text[m.end() : m.end() + 80]
                nxt = clean_line(after.splitlines()[0] if after.splitlines() else "")
                if nxt and len(nxt) < 40 and "。" not in nxt:
                    cap = f"表 {m.group(2)}：{nxt}"
                else:
                    cap = f"表 {m.group(2)}"
            curated.append((pi, "表", m.group(2), cap))
            curated_pages.add(pi)

    # Auto-include remaining chapter grid tables (h+v lines) not already captured
    for ch, (a, b) in CHAPTER_RANGES.items():
        for pi in range(a, b + 1):
            if pi in curated_pages:
                continue
            page = doc[pi]
            hlines, vlines, _ = count_grid_lines(page)
            if hlines >= 5 and vlines >= 2:
                text = page.get_text() or ""
                # skip pure org-chart pages already covered via 圖 captions
                if re.search(r"圖\s*\d+\s*[：:︰]", text):
                    continue
                caption = f"第 {ch} 章圖表（PDF 第 {pi + 1} 頁）"
                if "交易時間" in text or "現行安排" in text:
                    caption = "聯交所交易時間（現行安排）"
                elif "概要" in text and "牌照" in text:
                    caption = "受規管活動牌照涵蓋範圍概要"
                curated.append((pi, "表", f"auto{pi+1}", caption))
                curated_pages.add(pi)

    for pi, kind, num, caption in curated:
        page = doc[pi]
        clip = clip_for_visual(page, kind, caption)
        ch = chapter_of(pi)
        fname = f"ch{ch}-p{pi+1:03d}.png"
        out_path = fig_dir / fname
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
        pix.save(str(out_path))
        rel = f"figures/{fname}"
        print(f"  figure page {pi+1}: {fname} ({pix.width}x{pix.height}) {caption[:40]}")

        key = f"{kind}{num}"
        scoped = f"ch{ch}-{key}"
        meta = {
            "src": rel,
            "alt": caption,
            "caption": caption,
            "pdfPage": pi + 1,
            "chapter": ch,
            "figureNum": str(num),
            "kind": "table" if kind == "表" else "figure",
        }
        figures[scoped] = meta
        figures[key] = meta
        figures[f"p{pi+1}-{key}"] = meta
        figures[f"{kind} {num}"] = meta

    return figures



def extract_chapter(
    reader: PdfReader,
    ch: int,
    figures: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    toc_text = reader.pages[TOC_PAGES[ch] - 1].extract_text() or ""
    toc_sections = parse_toc_sections(toc_text)
    for sid, title in [("overview", "本章概覽"), ("objectives", "學習重點")]:
        if not any(s["id"] == sid for s in toc_sections):
            toc_sections.insert(0 if sid == "overview" else 1, {"id": sid, "title": title})

    match_header = build_header_matcher(toc_sections)
    start, end = CHAPTER_RANGES[ch]
    all_lines: List[str] = []
    for pi in range(start, end + 1):
        all_lines.extend(clean_page_text(reader.pages[pi].extract_text() or ""))

    fig_lookup = {}
    for k, v in figures.items():
        if v.get("chapter") == ch:
            kind = "表" if v.get("kind") == "table" else "圖"
            fig_lookup[f"{kind}{v['figureNum']}"] = v
            fig_lookup[k] = v

    sections_out: List[Dict[str, Any]] = []
    current_id = "body"
    current_title = "本章內容"
    buf: List[str] = []

    def push() -> None:
        nonlocal buf, current_id, current_title
        if not buf and current_id == "body":
            return
        blocks = lines_to_blocks(buf, fig_lookup)
        if blocks:
            sections_out.append({"id": current_id, "title": current_title, "blocks": blocks})
        buf = []

    for line in all_lines:
        hit = match_header(line)
        if hit:
            push()
            current_id, current_title = hit
            continue
        buf.append(line)
    push()

    extracted_ids = {s["id"] for s in sections_out}
    nav = []
    for s in toc_sections:
        nav.append({"id": s["id"], "title": s["title"], "available": s["id"] in extracted_ids})
    for s in sections_out:
        if not any(n["id"] == s["id"] for n in nav):
            nav.append({"id": s["id"], "title": s["title"], "available": True})

    # Attach chapter figures list for gallery / fallback
    chapter_figs = [
        v
        for k, v in figures.items()
        if v.get("chapter") == ch and k.startswith(f"ch{ch}-")
    ]
    # dedupe by src
    seen_src = set()
    unique_figs = []
    for f in chapter_figs:
        if f["src"] in seen_src:
            continue
        seen_src.add(f["src"])
        unique_figs.append(f)

    # Inject chapter figures that were not inlined (e.g. unlabeled summary tables)
    used_src = {
        b.get("src")
        for s in sections_out
        for b in s["blocks"]
        if b.get("type") == "figure" and b.get("src")
    }
    orphans = [f for f in unique_figs if f.get("src") and f["src"] not in used_src]
    if orphans:
        for fig in orphans:
            placed = False
            needles: List[str] = []
            if fig.get("figureNum") == "1" and fig.get("kind") == "table":
                needles.append("表1")
                needles.append("表 1")
            caption = fig.get("caption") or ""
            if "交易時間" in caption or "現行安排" in caption:
                needles.extend(["交易時間", "現行安排", "開市前時段"])
            if "牌照涵蓋" in caption or "概要" in caption:
                needles.extend(["概要", "牌照涵蓋"])
            for s in sections_out:
                for idx, b in enumerate(list(s["blocks"])):
                    text = (b.get("text") or "").replace(" ", "")
                    if needles and any(n.replace(" ", "") in text for n in needles):
                        s["blocks"].insert(
                            idx + 1,
                            {
                                "type": "figure",
                                "caption": fig["caption"],
                                "figureId": f"{'表' if fig.get('kind')=='table' else '圖'}{fig['figureNum']}",
                                "kind": fig.get("kind") or "figure",
                                "src": fig["src"],
                                "alt": fig.get("alt") or fig["caption"],
                            },
                        )
                        placed = True
                        break
                    if (not needles) and any(k in (b.get("text") or "") for k in ("概要", "牌照涵蓋", "組織架構", "交易時間")):
                        s["blocks"].insert(
                            idx + 1,
                            {
                                "type": "figure",
                                "caption": fig["caption"],
                                "figureId": f"extra-{fig['pdfPage']}",
                                "kind": fig.get("kind") or "figure",
                                "src": fig["src"],
                                "alt": fig.get("alt") or fig["caption"],
                            },
                        )
                        placed = True
                        break
                if placed:
                    break
            if not placed:
                target = next(
                    (s for s in reversed(sections_out) if s["id"] not in {"summary", "keypoints"}),
                    sections_out[-1] if sections_out else None,
                )
                if target:
                    target["blocks"].append(
                        {
                            "type": "figure",
                            "caption": fig["caption"],
                            "figureId": f"extra-{fig['pdfPage']}",
                            "kind": fig.get("kind") or "figure",
                            "src": fig["src"],
                            "alt": fig.get("alt") or fig["caption"],
                        }
                    )

    return {
        "id": str(ch),
        "number": ch,
        "title": CHAPTER_TITLES[ch],
        "fullTitle": f"第 {ch} 章：{CHAPTER_TITLES[ch]}",
        "pdfPageStart": start + 1,
        "pdfPageEnd": end + 1,
        "nav": nav,
        "sections": sections_out,
        "figures": unique_figs,
    }


def extract_updates(reader: PdfReader) -> Dict[str, Any]:
    texts = []
    for i in range(290, min(292, len(reader.pages))):
        texts.append(reader.pages[i].extract_text() or "")
    body = "\n".join(clean_page_text("\n".join(texts)))
    return {
        "title": "2.8 版的主要更新",
        "updatedAt": "2016-08",
        "updatedAtLabel": "更新於 2016 年 8 月",
        "text": body,
    }


def main() -> None:
    version_dir = OUT_ROOT / VERSION_ID
    chapters_dir = version_dir / "chapters"
    extras_dir = version_dir / "extras"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    extras_dir.mkdir(parents=True, exist_ok=True)

    print("Extracting figures...")
    doc = fitz.open(str(PDF))
    figures = extract_figures(doc, version_dir)
    print(f"figures mapped: {len(figures)}")

    reader = PdfReader(str(PDF))
    chapter_summaries = []
    for ch in range(1, 10):
        print(f"Extracting chapter {ch}...")
        data = extract_chapter(reader, ch, figures)
        (chapters_dir / f"{ch:02d}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        fig_count = sum(1 for s in data["sections"] for b in s["blocks"] if b.get("type") == "figure")
        chapter_summaries.append(
            {
                "id": data["id"],
                "number": ch,
                "title": data["title"],
                "fullTitle": data["fullTitle"],
                "sectionCount": len(data["sections"]),
                "figureCount": len(data.get("figures") or []),
                "nav": [{"id": n["id"], "title": n["title"]} for n in data["nav"] if n.get("available")],
                "file": f"chapters/{ch:02d}.json",
            }
        )
        print(
            f"  sections={len(data['sections'])} inline_figures={fig_count} "
            f"chapter_figures={len(data.get('figures') or [])}"
        )

    updates = extract_updates(reader)
    (extras_dir / "updates-2.8.json").write_text(
        json.dumps(updates, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    meta = {
        **META,
        "extractedAt": datetime.now().isoformat(timespec="seconds"),
        "chapterCount": 9,
        "chapters": chapter_summaries,
        "extras": [
            {
                "id": "updates-2.8",
                "title": "2.8 版的主要更新（2016年8月）",
                "file": "extras/updates-2.8.json",
            }
        ],
    }
    (version_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    index = {
        "currentVersion": VERSION_ID,
        "availableVersions": [
            {
                "versionId": VERSION_ID,
                "versionLabel": "2.8",
                "updatedThrough": "2016-08",
                "updatedThroughLabel": "2016年8月",
                "edition": "第二版",
                "path": f"{VERSION_ID}/meta.json",
            }
        ],
        "howToUpdate": [
            "將新版 PDF 匯出到 public/data/manual/<newVersionId>/（含 figures/）",
            "更新 index.json 的 currentVersion",
            "舊版可保留以便對照",
        ],
    }
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Done", VERSION_ID)


if __name__ == "__main__":
    main()
