#!/usr/bin/env python3
"""Parse 2CEXAM mock-test PDF (text layer) and merge into questions.json."""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF = Path("/Users/priskenlo/Downloads/1024422648-HKSI-P1-mock-test-1.pdf")
BANK = ROOT / "public" / "data" / "questions.json"

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

FOOTER_RE = re.compile(
    r"^(第\s*\d+\s*頁|Website:|請各考生留意|券及投資學會亦沒有|2CEXAM 模擬試題|"
    r"證券及期貨從業員資格考試|卷\(一\))"
)
META_TAIL_RE = re.compile(
    r"章節\n小章節\n答案\n部分\n"
    r"(\d+)\n"
    r"(\d+)\n"
    r"題庫號\n"
    r"熱門\n"
    r"(\d+)\n"
    r"(?:(\d+)\n)?"
    r"(?:(\d+)\n)?"
)


def normalize_key(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("\x00", "")
    s = s.replace(" ", "").replace("\n", "")
    s = s.replace("？", "?").replace("﹖", "?")
    s = re.sub(r"[，。、；：:．，.]", "", s)
    s = re.split(r"I\.|II\.|III\.|IV\.", s)[0]
    return s[:80]


def clean_text(s: str) -> str:
    s = (s or "").replace("\x00", "").replace("\u0000", "")
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def extract_lines(doc: fitz.Document) -> List[str]:
    lines: List[str] = []
    # Content is pages 2..203-ish (index 1..202); skip cover + trailing fliphtml junk
    end = min(doc.page_count, 203)
    for i in range(1, end):
        text = doc[i].get_text() or ""
        for raw in text.splitlines():
            ln = clean_text(raw)
            if not ln:
                continue
            if FOOTER_RE.match(ln):
                continue
            lines.append(ln)
    return lines


def find_meta_spans(lines: List[str]) -> List[Tuple[int, int, Dict[str, Any]]]:
    """Return list of (meta_start_idx, meta_end_idx_exclusive, meta_dict)."""
    spans = []
    i = 0
    n = len(lines)
    while i < n - 6:
        if (
            lines[i] == "章節"
            and lines[i + 1] == "小章節"
            and lines[i + 2] == "答案"
            and lines[i + 3] == "部分"
            and lines[i + 4].isdigit()
            and lines[i + 5].isdigit()
            and i + 7 < n
            and lines[i + 6] == "題庫號"
            and lines[i + 7] == "熱門"
        ):
            qnum = int(lines[i + 4])
            bank_id = lines[i + 5]
            j = i + 8
            nums: List[int] = []
            while j < n and lines[j].isdigit() and len(nums) < 3:
                nums.append(int(lines[j]))
                j += 1
            chapter = nums[0] if nums else None
            sub = nums[1] if len(nums) > 1 else None
            section = nums[2] if len(nums) > 2 else None
            if chapter is not None and not (1 <= chapter <= 9):
                chapter = None
            spans.append(
                (
                    i,
                    j,
                    {
                        "number": qnum,
                        "bankId": bank_id,
                        "chapter": chapter,
                        "subchapter": sub,
                        "section": str(section) if section is not None else None,
                    },
                )
            )
            i = j
            continue
        i += 1
    return spans


def parse_body(body_lines: List[str], meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse stem/options/answer from lines preceding a metadata block."""
    if len(body_lines) < 6:
        return None

    # Expect trailing: ANSWER, A, B, C, D
    if body_lines[-4:] != ["A", "B", "C", "D"]:
        return None
    answer = body_lines[-5].strip().upper()
    if answer not in "ABCD":
        return None

    head = body_lines[:-5]
    if len(head) < 5:
        return None

    # Last 4 lines of head are options A-D text
    opt_vals = [clean_text(x) for x in head[-4:]]
    stem_lines = head[:-4]
    if not stem_lines or any(not v for v in opt_vals):
        return None

    # Join stem: keep newlines for roman items
    stem_parts: List[str] = []
    for ln in stem_lines:
        if re.match(r"^(I{1,3}|IV)\.\s*", ln):
            stem_parts.append(ln)
        elif stem_parts and re.match(r"^(I{1,3}|IV)\.\s*", stem_parts[-1]):
            stem_parts.append(ln)
        else:
            if stem_parts and not re.match(r"^(I{1,3}|IV)\.\s*", stem_parts[-1]):
                # continue previous prose
                if re.search(r"[\u4e00-\u9fffA-Za-z0-9]$", stem_parts[-1]) and re.match(
                    r"^[\u4e00-\u9fff]", ln
                ):
                    stem_parts[-1] += ln
                else:
                    stem_parts.append(ln)
            else:
                stem_parts.append(ln)

    stem = "\n".join(stem_parts).strip()
    stem = re.sub(r"\n{3,}", "\n\n", stem)
    if len(stem) < 4:
        return None

    options = {"A": opt_vals[0], "B": opt_vals[1], "C": opt_vals[2], "D": opt_vals[3]}
    if len(set(options.values())) < 2:
        return None

    chapter = meta.get("chapter")
    return {
        "id": f"mock1-{meta['number']}",
        "number": meta["number"],
        "bankId": meta.get("bankId"),
        "chapter": chapter,
        "subchapter": meta.get("subchapter"),
        "section": meta.get("section"),
        "stem": stem,
        "options": options,
        "answer": answer,
        "explanation": "",
        "hot": False,
        "chapterTitle": CHAPTER_TITLES.get(chapter or 0, ""),
        "source": PDF.name,
    }


def parse_pdf() -> Tuple[List[Dict[str, Any]], List[str]]:
    doc = fitz.open(str(PDF))
    lines = extract_lines(doc)
    spans = find_meta_spans(lines)
    questions: List[Dict[str, Any]] = []
    errors: List[str] = []

    prev_end = 0
    for meta_start, meta_end, meta in spans:
        body = lines[prev_end:meta_start]
        # Drop leading junk labels if any
        while body and body[0] in {"章節", "小章節", "答案", "部分", "題庫號", "熱門"}:
            body = body[1:]
        q = parse_body(body, meta)
        if q is None:
            preview = " | ".join(body[-8:])[:160]
            errors.append(f"Q{meta.get('number')}: parse fail near: {preview}")
        else:
            questions.append(q)
        prev_end = meta_end

    # Forward-fill missing chapters
    last_ch = None
    for q in questions:
        if q["chapter"]:
            last_ch = q["chapter"]
        elif last_ch:
            q["chapter"] = last_ch
            q["chapterTitle"] = CHAPTER_TITLES.get(last_ch, "")

    # Dedup by question number within this PDF
    seen = set()
    unique = []
    for q in questions:
        if q["number"] in seen:
            continue
        seen.add(q["number"])
        unique.append(q)
    unique.sort(key=lambda q: q["number"])
    return unique, errors


def merge_into_bank(new_qs: List[Dict[str, Any]]) -> Dict[str, Any]:
    if BANK.exists():
        bank = json.loads(BANK.read_text(encoding="utf-8"))
    else:
        bank = {
            "source": "",
            "questions": [],
            "chapters": {str(k): v for k, v in CHAPTER_TITLES.items()},
        }

    existing = bank.get("questions", [])
    by_key = {}
    for q in existing:
        by_key[normalize_key(q.get("stem", ""))] = q

    added = 0
    updated_ans = 0
    skipped_dup = 0
    for q in new_qs:
        key = normalize_key(q["stem"])
        if not key:
            continue
        if key in by_key:
            old = by_key[key]
            # Same stem: keep existing, but fill blank explanation / prefer mock chapter if missing
            skipped_dup += 1
            if not old.get("chapter") and q.get("chapter"):
                old["chapter"] = q["chapter"]
                old["chapterTitle"] = q["chapterTitle"]
            if old.get("answer") != q["answer"]:
                # Prefer new mock answer only if old options look broken; else keep old
                pass
            continue

        # New question — renumber id to avoid collisions; keep mock number in bankId
        q["id"] = f"mock1-{q['number']}"
        existing.append(q)
        by_key[key] = q
        added += 1

    # Stable sort: by chapter then number then id
    existing.sort(
        key=lambda q: (
            q.get("chapter") or 99,
            q.get("number") or 0,
            str(q.get("id") or ""),
        )
    )

    sources = []
    if bank.get("source"):
        sources.append(bank["source"])
    if PDF.name not in sources:
        sources.append(PDF.name)

    bank["source"] = " + ".join(sources)
    bank["extractedAt"] = datetime.now().isoformat(timespec="seconds")
    bank["total"] = len(existing)
    bank["chapters"] = {str(k): v for k, v in CHAPTER_TITLES.items()}
    bank["questions"] = existing
    notes = bank.get("notes") or []
    note = f"Merged {PDF.name}: +{added} new, {skipped_dup} duplicate stems skipped."
    notes = [n for n in notes if not n.startswith("Merged 1024422648")]
    notes.append(note)
    bank["notes"] = notes
    bank["_mergeStats"] = {"added": added, "skippedDup": skipped_dup, "updatedAns": updated_ans}
    return bank


def main() -> None:
    qs, errors = parse_pdf()
    print(f"parsed {len(qs)} from mock PDF, errors {len(errors)}")
    print("by chapter", dict(sorted(Counter(q["chapter"] for q in qs).items())))
    if errors[:5]:
        print("sample errors:")
        for e in errors[:5]:
            print(" ", e)

    # Sanity samples
    for n in [1, 2, 5, 11, 390, 791]:
        q = next((x for x in qs if x["number"] == n), None)
        if not q:
            print(f"missing Q{n}")
            continue
        print(f"Q{n} ch={q['chapter']} ans={q['answer']} bank={q['bankId']}")
        print(" ", q["stem"][:70].replace("\n", " | "))
        print(" ", q["options"])

    # Quality gate
    bad = []
    for q in qs:
        if len(q["options"]) != 4:
            bad.append((q["number"], "opts"))
        if q["answer"] not in q["options"]:
            bad.append((q["number"], "ans"))
        if len(set(q["options"].values())) < 2:
            bad.append((q["number"], "dup"))
        if not q.get("chapter"):
            bad.append((q["number"], "ch"))
    print("quality issues", len(bad), bad[:15])

    bank = merge_into_bank(qs)
    BANK.write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding="utf-8")
    stats = bank["_mergeStats"]
    del bank["_mergeStats"]
    BANK.write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"bank total={bank['total']} added={stats['added']} skipped_dup={stats['skippedDup']}"
    )
    print(
        "final by chapter",
        dict(sorted(Counter(q.get("chapter") for q in bank["questions"]).items())),
    )


if __name__ == "__main__":
    main()
