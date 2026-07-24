#!/usr/bin/env python3
"""Extract HKSI practice questions from scanned 2CEXAM PDF via macOS Vision OCR."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PDF = Path("/Users/priskenlo/Downloads/522363077-LE-HKSI-Paper-1-Practice-Questions.pdf")
OCR_BIN = ROOT / ".tmp" / "vision_ocr_box"
OUT_DIR = ROOT / ".tmp" / "pages"
OUT_JSON = ROOT / "public" / "data" / "questions.json"
SCALE = 2.5

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


def ocr_page(img_path: Path) -> list[dict]:
    raw = subprocess.check_output([str(OCR_BIN), str(img_path)], text=True, errors="replace")
    return json.loads(raw)


def fix_roman(text: str) -> str:
    """Common OCR fixes for Traditional Chinese MCQ roman numerals."""
    # 皿 is a frequent misread of III
    text = text.replace("皿", "III")
    # Fix patterns like "I." that should be "II." when duplicated oddly is hard;
    # normalize fullwidth punctuation
    text = text.replace("，", ",").replace("．", ".")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def label_match(text: str, label: str) -> bool:
    """True if text contains label as its own token (章節 must not match 小章節)."""
    if label == "章節":
        return bool(re.search(r"(?<![小])章節", text))
    return label in text


def near_label_value(lines: list[dict], label: str, y0: float, y1: float, x_min: float = 0.65) -> str | None:
    """Find a value associated with a metadata label within a y-band."""
    # Metadata header often sits slightly above the question number baseline.
    y0e, y1e = y0 - 0.02, y1
    label_hits = [L for L in lines if L["x"] >= x_min and y0e <= L["y"] <= y1e and label_match(L["text"], label)]
    if not label_hits:
        return None
    lab = min(label_hits, key=lambda L: abs(L["y"] - y0))
    # Same line value after label
    m = re.search(rf"{re.escape(label)}\s*[:：]?\s*([A-D0-9]+)", lab["text"])
    if m and not (label == "章節" and "小章節" in lab["text"]):
        return m.group(1)
    # Prefer numeric/token on same horizontal line to the right
    same_line = []
    below = []
    for L in lines:
        if L["x"] < x_min or not (y0e <= L["y"] <= y1e):
            continue
        if L is lab:
            continue
        token = L["text"].strip()
        if not re.fullmatch(r"[A-D0-9]+", token):
            continue
        dy = L["y"] - lab["y"]
        if abs(dy) < 0.02 and L["x"] > lab["x"]:
            same_line.append((L["x"], token))
        elif 0 <= dy < 0.035:
            below.append((dy, token))
    if same_line:
        same_line.sort()
        return same_line[0][1]
    # For 章節 only: NEVER take the number below — that is usually 小章節/部分.
    if label == "章節":
        return None
    if below:
        below.sort()
        return below[0][1]
    return None


def extract_answer(lines: list[dict], y0: float, y1: float) -> str | None:
    y0e = y0 - 0.02
    for L in lines:
        if L["x"] < 0.65 or not (y0e <= L["y"] <= y1):
            continue
        m = re.search(r"答案\s*[:：]?\s*([A-Da-d])", L["text"])
        if m:
            return m.group(1).upper()
    band = " ".join(L["text"] for L in lines if L["x"] >= 0.65 and y0e <= L["y"] <= y1)
    m = re.search(r"答案\s*[:：]?\s*([A-Da-d])", band)
    return m.group(1).upper() if m else None


def is_hot(lines: list[dict], y0: float, y1: float) -> bool:
    for L in lines:
        if L["x"] < 0.65 or not (y0 <= L["y"] <= y1):
            continue
        t = L["text"]
        if "熱門" in t and ("☑" in t or "✓" in t or "√" in t or "x" in t.lower() or "X" in t):
            # checkbox often OCR'd poorly; if 熱門 line has trailing mark beyond empty box
            if re.search(r"熱門\s*[☑✓√Xx×]", t):
                return True
    return False


def cluster_questions(lines: list[dict]) -> list[tuple[int, float, float]]:
    """Return list of (qnum, y_start, y_end) for left-column question starts."""
    starts = []
    for L in lines:
        if L["x"] > 0.20:
            continue
        m = re.match(r"^(\d{1,4})(?:\s|$)", L["text"].strip())
        if not m:
            continue
        # question numbers on left are usually < 2000 and appear as own token or start of stem
        qn = int(m.group(1))
        if qn < 1 or qn > 5000:
            continue
        # Prefer short lines that are just the number, or number + stem
        if L["w"] < 0.08 or re.match(r"^\d{1,4}\s+\S", L["text"].strip()) or re.fullmatch(r"\d{1,4}", L["text"].strip()):
            starts.append((qn, L["y"]))
    # Deduplicate near-identical y
    starts.sort(key=lambda x: x[1])
    cleaned = []
    for qn, y in starts:
        if cleaned and abs(cleaned[-1][1] - y) < 0.02:
            continue
        cleaned.append((qn, y))
    result = []
    for i, (qn, y) in enumerate(cleaned):
        y1 = cleaned[i + 1][1] - 0.005 if i + 1 < len(cleaned) else 0.92
        result.append((qn, y, y1))
    return result


def parse_block(lines: list[dict], qn: int, y0: float, y1: float) -> dict | None:
    left = [L for L in lines if L["x"] < 0.70 and y0 - 0.005 <= L["y"] <= y1]
    right = [L for L in lines if L["x"] >= 0.65 and y0 - 0.005 <= L["y"] <= y1]

    # Chapter
    chapter = near_label_value(lines, "章節", y0, y1)
    subchapter = near_label_value(lines, "小章節", y0, y1)
    section = near_label_value(lines, "部分", y0, y1)
    bank_id = near_label_value(lines, "題庫號", y0, y1)
    # OCR often misreads 題庫號
    if bank_id is None:
        for label in ("題庫號", "題車號", "題啡號", "題审號", "題軍號", "題咏號", "題唓號"):
            bank_id = near_label_value(lines, label, y0, y1)
            if bank_id:
                break
    answer = extract_answer(lines, y0, y1)

    # Build left text in reading order
    left_sorted = sorted(left, key=lambda L: (round(L["y"], 3), L["x"]))
    texts = [fix_roman(L["text"]) for L in left_sorted]

    # Remove leading question number token
    joined_lines = []
    for t in texts:
        if not joined_lines and re.fullmatch(rf"{qn}", t):
            continue
        if not joined_lines:
            t = re.sub(rf"^{qn}\s+", "", t)
        joined_lines.append(t)

    # Split options / explanation
    option_re = re.compile(r"^([A-D])[\.．、:\s]*(.*)$")
    options: dict[str, str] = {}
    stem_parts = []
    expl_parts = []
    mode = "stem"  # stem -> options -> explanation
    for t in joined_lines:
        # Skip footer noise
        if "Website:" in t or "www.2cexam" in t or "請各考生留意" in t or re.match(r"第\s*\d+\s*頁", t):
            continue
        om = option_re.match(t)
        if om and mode in ("stem", "options"):
            key = om.group(1)
            rest = om.group(2).strip()
            # Avoid treating "A class of..." mid-explanation; options usually early
            if key not in options:
                options[key] = rest
                mode = "options"
                continue
        if mode == "options" and not om:
            # likely start of explanation once we have >=2 options
            if len(options) >= 2:
                mode = "explanation"
                expl_parts.append(t)
                continue
            stem_parts.append(t)
            continue
        if mode == "explanation":
            expl_parts.append(t)
        else:
            stem_parts.append(t)

    stem = fix_roman("".join(stem_parts) if len("".join(stem_parts)) < 40 else "\n".join(stem_parts))
    # Prefer joining stem with spaces/newlines carefully
    stem = "\n".join(p for p in stem_parts if p).strip()
    stem = fix_roman(stem)
    explanation = fix_roman("\n".join(expl_parts).strip())

    # Normalize options
    for k in list(options):
        options[k] = fix_roman(options[k])

    if not stem or not answer or len(options) < 2:
        return None

    try:
        chapter_i = int(chapter) if chapter and chapter.isdigit() else None
    except Exception:
        chapter_i = None
    if chapter_i is not None and chapter_i not in range(1, 10):
        chapter_i = None

    return {
        "id": f"q-{qn}",
        "number": qn,
        "bankId": bank_id,
        "chapter": chapter_i,
        "subchapter": int(subchapter) if subchapter and subchapter.isdigit() else None,
        "section": section,
        "stem": stem,
        "options": {k: options.get(k, "") for k in "ABCD" if k in options},
        "answer": answer,
        "explanation": explanation,
        "hot": is_hot(lines, y0, y1),
        "chapterTitle": CHAPTER_TITLES.get(chapter_i or 0, ""),
    }


def render_and_ocr(doc: fitz.Document, page_index: int) -> list[dict]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img_path = OUT_DIR / f"page_{page_index + 1:03d}.png"
    ocr_path = OUT_DIR / f"page_{page_index + 1:03d}.ocr.json"
    if ocr_path.exists():
        return json.loads(ocr_path.read_text(encoding="utf-8"))
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE))
    pix.save(str(img_path))
    lines = ocr_page(img_path)
    ocr_path.write_text(json.dumps(lines, ensure_ascii=False), encoding="utf-8")
    return lines


def main():
    if not OCR_BIN.exists():
        print("Missing OCR binary", OCR_BIN, file=sys.stderr)
        sys.exit(1)
    doc = fitz.open(str(PDF))
    start = int(os.environ.get("START_PAGE", "0"))
    end = int(os.environ.get("END_PAGE", str(doc.page_count)))
    questions: list[dict] = []
    failures: list[dict] = []

    for i in range(start, min(end, doc.page_count)):
        print(f"OCR page {i + 1}/{doc.page_count}...", flush=True)
        try:
            lines = render_and_ocr(doc, i)
        except Exception as e:
            print(f"  FAIL render/ocr: {e}", flush=True)
            failures.append({"page": i + 1, "error": str(e)})
            continue
        blocks = cluster_questions(lines)
        print(f"  found {len(blocks)} question blocks", flush=True)
        for qn, y0, y1 in blocks:
            q = parse_block(lines, qn, y0, y1)
            if q is None:
                failures.append({"page": i + 1, "number": qn, "error": "parse_failed"})
                continue
            q["sourcePage"] = i + 1
            questions.append(q)

    # Deduplicate by number keeping first
    seen = set()
    unique = []
    for q in questions:
        if q["number"] in seen:
            continue
        seen.add(q["number"])
        unique.append(q)
    unique.sort(key=lambda q: q["number"])

    # Forward-fill missing chapters; dampen impossible jumps (OCR often swaps 小章節 into 章節)
    last_ch = None
    for q in unique:
        ch = q["chapter"]
        if ch is None:
            if last_ch:
                q["chapter"] = last_ch
                q["chapterTitle"] = CHAPTER_TITLES.get(last_ch, "")
            continue
        if last_ch is not None and ch > last_ch + 1 and ch >= 5:
            # Likely misread subsection as chapter — keep previous until a stable new chapter appears
            q["chapter"] = last_ch
            q["chapterTitle"] = CHAPTER_TITLES.get(last_ch, "")
            continue
        last_ch = ch
        q["chapterTitle"] = CHAPTER_TITLES.get(ch, "")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": str(PDF.name),
        "extractedAt": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "total": len(unique),
        "chapters": CHAPTER_TITLES,
        "questions": unique,
        "failures": failures,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Stats
    from collections import Counter
    c = Counter(q["chapter"] for q in unique)
    print("\nDone.")
    print(f"Questions: {len(unique)}")
    print(f"Failures: {len(failures)}")
    print("By chapter:", dict(sorted((k or 0, v) for k, v in c.items())))


if __name__ == "__main__":
    main()
