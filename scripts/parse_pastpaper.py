#!/usr/bin/env python3
"""Parse the text-based HKSI Paper 1 past paper PDF into questions.json."""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF = Path("/Users/priskenlo/Downloads/871245770-HKSI-Paper-1-Pastpaper.pdf")
OUT = ROOT / "public" / "data" / "questions.json"
OLD = ROOT / "public" / "data" / "questions_scanned_backup.json"

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


def clean_lines(s: str) -> List[str]:
    lines: List[str] = []
    for line in s.splitlines():
        line = line.strip()
        if not line:
            continue
        if line in {"✓", "✔", "√"}:
            continue
        if "Paradox" in line or line.startswith("Publisher"):
            continue
        if re.fullmatch(r"HKSIP1C\s*\[[^\]]+\]", line):
            continue
        if line in {"www.2cexam.com", "All Rights Reserved"}:
            continue
        lines.append(line)
    return lines


def is_section_ref_line(line: str) -> bool:
    """True for syllabus refs like 4.3.12 or 6.3.16 & — not bare page numbers."""
    if line == "&":
        return True
    if re.fullmatch(r"[0-9]+\.[0-9]+(?:\.[0-9]+)*(?:\s*&)?", line):
        return True
    if re.fullmatch(r"[0-9]+\.[0-9].*", line) and "&" in line:
        return True
    # chapter-only refs used early in the book: single digit 1-9
    if re.fullmatch(r"[1-9]", line):
        return True
    return False


def join_cjk(parts: List[str]) -> str:
    if not parts:
        return ""
    out = parts[0]
    for p in parts[1:]:
        if out and re.search(r"[\u4e00-\u9fffA-Za-z0-9％%]$", out) and re.match(
            r"^[\u4e00-\u9fff]", p
        ):
            out += p
        else:
            out += " " + p
    return re.sub(r"\s+", " ", out).strip()


def parse_block(block: str) -> Optional[Dict[str, Any]]:
    lines = clean_lines(block)
    if not lines:
        return None
    m = re.match(r"^(\d{1,4})\.(.*)$", lines[0])
    if not m:
        return None
    num = int(m.group(1))
    rest0 = m.group(2).strip()
    body = ([rest0] if rest0 else []) + lines[1:]

    answer = None
    section_ref = None
    i = len(body) - 1
    ref_chunks: List[str] = []
    while i >= 0 and is_section_ref_line(body[i]):
        # Don't treat a lone chapter digit as ref if it would leave no answer
        ref_chunks.append(body[i])
        i -= 1
    # If we consumed a lone 1-9 but previous isn't an answer letter, put it back
    if ref_chunks and re.fullmatch(r"[1-9]", ref_chunks[-1]) and (
        i < 0 or not re.fullmatch(r"[A-D]", body[i])
    ):
        # restore until we find answer or give up
        while ref_chunks and not (
            i >= 0 and re.fullmatch(r"[A-D]", body[i])
        ):
            body_restored = ref_chunks.pop()
            # actually we need to re-append to body logically — simpler: re-scan
            break

    # Cleaner end-scan:
    answer = None
    section_ref = None
    cut = len(body)
    # Find last answer letter
    for j in range(len(body) - 1, max(-1, len(body) - 12), -1):
        if re.fullmatch(r"[A-D]", body[j]):
            # Ensure following lines look like section refs / end
            trailing = body[j + 1 :]
            if trailing and not all(is_section_ref_line(t) for t in trailing):
                # allow trailing page-number-only noise
                ok = True
                refs = []
                for t in trailing:
                    if is_section_ref_line(t):
                        refs.append(t)
                    elif re.fullmatch(r"\d{1,3}", t):
                        continue  # page number
                    else:
                        ok = False
                        break
                if not ok:
                    continue
                answer = body[j]
                section_ref = " ".join(refs).strip() or None
                cut = j
                break
            else:
                answer = body[j]
                refs = [t for t in trailing if is_section_ref_line(t)]
                section_ref = " ".join(refs).strip() or None
                cut = j
                break
        mm = re.fullmatch(r"([A-D])\s+([0-9].*)", body[j])
        if mm:
            answer = mm.group(1)
            section_ref = mm.group(2).strip()
            cut = j
            break

    if not answer:
        return None

    content = body[:cut]
    opt_idx: Dict[str, int] = {}
    for idx, line in enumerate(content):
        if re.fullmatch(r"[A-D]\.?", line) or re.match(r"^[A-D]\.\s+\S", line):
            key = line[0]
            if key not in opt_idx:
                opt_idx[key] = idx
    if len(opt_idx) < 4:
        # still accept if 4 found later — require 4 for quality
        pass
    if len(opt_idx) < 2:
        return None

    first_opt = min(opt_idx.values())
    stem_lines = content[:first_opt]
    stem = "\n".join(stem_lines).strip()
    stem = re.sub(r"(?m)^(I{1,3}|IV)\.\s*\n\s*", r"\1. ", stem)
    stem = re.sub(r"(?<=[\u4e00-\u9fff])\n(?=[\u4e00-\u9fff])", "", stem)
    stem = re.sub(r"[ \t]+", " ", stem)
    stem = re.sub(r"\n{3,}", "\n\n", stem).strip()

    options: Dict[str, str] = {}
    keys_sorted = sorted(opt_idx.items(), key=lambda kv: kv[1])
    for n, (key, idx) in enumerate(keys_sorted):
        end = keys_sorted[n + 1][1] if n + 1 < len(keys_sorted) else len(content)
        chunk = content[idx:end]
        first = re.sub(r"^[A-D]\.?\s*", "", chunk[0]).strip()
        parts = ([first] if first else []) + chunk[1:]
        options[key] = join_cjk(parts)

    chapter = None
    if section_ref:
        # normalize refs: drop stray bare page nums already excluded
        section_ref = re.sub(r"\s+", " ", section_ref).strip()
        mm = re.match(r"(\d+)", section_ref)
        if mm:
            chapter = int(mm.group(1))
            if chapter < 1 or chapter > 9:
                chapter = None

    if not stem or answer not in options or len(options) < 4:
        return None

    return {
        "id": f"pp-{num}",
        "number": num,
        "bankId": str(num),
        "chapter": chapter,
        "subchapter": None,
        "section": section_ref,
        "stem": stem,
        "options": {k: options[k] for k in "ABCD"},
        "answer": answer,
        "explanation": "",
        "hot": False,
        "chapterTitle": CHAPTER_TITLES.get(chapter or 0, ""),
        "source": PDF.name,
    }


def normalize_key(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace(" ", "").replace("\n", "")
    s = s.replace("？", "?").replace("﹖", "?")
    s = re.sub(r"[，。、；：:．，.]", "", s)
    s = re.split(r"I\.|II\.|III\.|IV\.", s)[0]
    return s[:70]


def apply_manual_fixes(questions: List[Dict[str, Any]]) -> List[str]:
    """Best-judgment fixes for known source/parse defects. Returns log lines."""
    log: List[str] = []
    by_num = {q["number"]: q for q in questions}

    # Q6: source mislabels II twice and omits IV; restore standard I–IV wording.
    # Correct pair is 評審結果為本 + 披露為本 → I, III (answer B).
    if 6 in by_num:
        q = by_num[6]
        q["stem"] = (
            "金融監管一般會以下列那兩類理念為本﹖\n"
            "I. 評審結果為本\n"
            "II. 懲罰為本\n"
            "III. 披露為本\n"
            "IV. 報酬為本"
        )
        q["explanation"] = (
            "香港金融監管一般以評審結果為本及披露為本（I、III）。"
            "原題羅馬數字標號錯亂（兩個 II、缺少 IV），已按溫習內容更正。"
        )
        log.append("Q6: fixed roman numeral labels I–IV")

    # Q227: source duplicates A/B as I,III — complete the 2×2 matrix; answer C stays
    if 227 in by_num:
        q = by_num[227]
        q["options"]["B"] = "I, IV"
        if "門檻" not in q["stem"] and "水平" not in q["stem"]:
            q["stem"] = (
                "《淡倉申報規則》要求市場參與者持有任何指明股份的須申報淡倉達到下列哪些水平時，"
                "須於申報日交易時間結束時申報淡倉。\n"
                "I. 1000 萬港元註冊資本\n"
                "II. 3000 萬港元\n"
                "III. 由法團發行的有關指明股份總數價值的 0.02％\n"
                "IV. 由法團發行的有關指明股份總數價值的 0.05％"
            )
        q["explanation"] = (
            "淡倉申報門檻為 3,000 萬港元或有關指明股份總數價值的 0.02%（以較低者為準的相關規定見溫習內容）；"
            "原題選項 A/B 相同屬排版錯誤，已修正 B 為 I, IV。"
        )
        log.append("Q227: fixed duplicate option B; clarified stem")

    # Q380: source omitted I–IV labels on four statements
    if 380 in by_num:
        q = by_num[380]
        q["stem"] = (
            "以下哪項是第一類專業投資者與第二類專業投資者的分別?\n"
            "I. 第一類專業投資者必然是法人(機構)，不能是有血有肉的自然人，"
            "第二類專業投資者則可以是法人(機構)也可以是自然人。\n"
            "II. 第一類專業投資者以業務性質來擬定，第二類則只以資產數目以及投資組合的規模擬定\n"
            "III. 第一類專業投資者的投資規模必定比第二類專業投資者的投資額大\n"
            "IV. 中介人並不需要對第一類專業投資者進行有關產品及市場有豐富的認識及具備足夠的"
            "專業知識及投資經驗評估，因為假定該機構有足夠能力應付。由於第二類投資者有可能是個人或"
            "主要業務並不是投資，因此中介人必須進行有關產品及市場有豐富的認識及具備足夠的專業知識及投資經驗評估。"
        )
        q["explanation"] = (
            "III 不正確：兩類專業投資者並非以「投資規模必定較大」區分。"
            "正確分別為 I、II、IV（答案 D）。原題缺羅馬數字標號，已補上。"
        )
        log.append("Q380: added missing I–IV labels on statements")

    # Q45: question asks 部門/科 but keyed answer is a committee — keep source key,
    # add note so learners aren't misled without changing keyed answer.
    if 45 in by_num:
        q = by_num[45]
        q["explanation"] = (
            "題目問「部門/科」。證監會企業融資部負責收購合併相關監管工作；"
            "「收購及合併委員會」屬委員會而非部門。本題依原題庫答案為 A，請同時留意用詞差異。"
        )
        log.append("Q45: added clarification note on department vs panel")

    return log


def review(q: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    opts = q["options"]
    if len(opts) != 4:
        problems.append("need_4_options")
    if q["answer"] not in opts:
        problems.append("bad_answer")
    vals = list(opts.values())
    if len(vals) != len(set(vals)):
        problems.append("dup_options")
    if any(not v.strip() for v in vals):
        problems.append("empty_option")
    if not q.get("chapter"):
        problems.append("no_chapter")
    if len(q["stem"]) < 8:
        problems.append("short_stem")
    # roman stem should mention IV if options use IV
    if any("IV" in v for v in vals) and "I." in q["stem"] and "IV." not in q["stem"]:
        # might still be ok for non-list stems
        if re.search(r"(?m)^I\.", q["stem"]):
            problems.append("missing_IV_in_stem")
    return problems


def main() -> None:
    # Backup previous scanned bank once
    scanned = ROOT / "public" / "data" / "questions.json"
    if scanned.exists() and not OLD.exists():
        data = json.loads(scanned.read_text(encoding="utf-8"))
        if data.get("source", "").startswith("522363077") or "Practice" in data.get(
            "source", ""
        ):
            OLD.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        elif data.get("questions") and data["questions"][0].get("id", "").startswith("q-"):
            OLD.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Also backup if current is OCR bank (id q-)
    if scanned.exists():
        data = json.loads(scanned.read_text(encoding="utf-8"))
        if data.get("questions") and str(data["questions"][0].get("id", "")).startswith("q-"):
            OLD.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print("backed up scanned bank to", OLD.name)

    raw = "\n".join((page.get_text() or "") for page in fitz.open(str(PDF)))
    text = raw
    text = re.sub(r"HKSIP1C\s*\[[^\]]+\]", "", text)
    text = re.sub(r"www\.2cexam\.com", "", text)
    text = re.sub(r"©\s*Paradox Management Limited", "", text)
    text = re.sub(r"All Rights Reserved", "", text)
    m = re.search(r"(?m)^1\.\s*$", text) or re.search(r"(?m)^1\.\s+\S", text)
    text = text[m.start() :] if m else text
    blocks = [p.strip() for p in re.split(r"(?m)^(?=\d{1,4}\.(?:\s|$))", text) if p.strip()]

    questions: List[Dict[str, Any]] = []
    failures = 0
    for b in blocks:
        q = parse_block(b)
        if not q:
            failures += 1
            continue
        questions.append(q)

    seen = set()
    unique: List[Dict[str, Any]] = []
    for q in questions:
        if q["number"] in seen:
            continue
        seen.add(q["number"])
        unique.append(q)
    unique.sort(key=lambda q: q["number"])

    # Merge short explanations from scanned backup where stems match and answers agree
    if OLD.exists():
        old = json.loads(OLD.read_text(encoding="utf-8"))
        expl_map = {}
        ans_map = {}
        for oq in old.get("questions", []):
            key = normalize_key(oq.get("stem", ""))
            if not key or len(key) < 12:
                continue
            ans_map[key] = oq.get("answer")
            expl = (oq.get("explanation") or "").strip()
            if len(expl) >= 15 and not re.search(r"皿|就菜|稀要|𥰆", expl):
                expl_map[key] = expl
        matched = 0
        for q in unique:
            key = normalize_key(q["stem"])
            if key in expl_map and ans_map.get(key) == q["answer"] and not q["explanation"]:
                q["explanation"] = expl_map[key]
                matched += 1
        print(f"merged explanations from scanned bank: {matched}")

    logs = apply_manual_fixes(unique)
    for line in logs:
        print("fix:", line)

    flagged = [(q["number"], review(q)) for q in unique]
    flagged = [(n, p) for n, p in flagged if p]
    print("parsed", len(unique), "failures", failures)
    print(
        "by chapter",
        dict(
            sorted(
                Counter(q["chapter"] for q in unique).items(),
                key=lambda x: (x[0] is None, x[0] or 0),
            )
        ),
    )
    print("remaining review flags", len(flagged), flagged[:20])

    payload = {
        "source": PDF.name,
        "extractedAt": datetime.now().isoformat(timespec="seconds"),
        "total": len(unique),
        "chapters": {str(k): v for k, v in CHAPTER_TITLES.items()},
        "notes": [
            "Primary bank from text-based past paper PDF (clean extract).",
            "Scanned practice PDF OCR bank was reviewed and replaced due to systematic OCR errors.",
            "Manual fixes applied where source typography was defective (see Q227, Q380).",
        ],
        "questions": unique,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT, "total", len(unique))


if __name__ == "__main__":
    main()
