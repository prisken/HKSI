#!/usr/bin/env python3
"""Map each question bank item to the best study-manual section.

Review approach:
1. Prefer question.subchapter when it matches a real content section id.
2. Score question stem/options against section titles + body keywords.
3. Apply chapter-specific topic boosts (answer-review specialist rules).
4. Write public/data/manual_refs.json and merge refs into questions.json.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
MANUAL_DIR = ROOT / "public" / "data" / "manual" / "v2.8-2016-08"
QUESTIONS = ROOT / "public" / "data" / "questions.json"
OUT_REFS = ROOT / "public" / "data" / "manual_refs.json"

SKIP_SECTIONS = {"overview", "objectives", "summary", "keypoints"}

# Chapter-specific topic → section boosts (manual-informed answer review)
TOPIC_RULES: Dict[int, List[Tuple[List[str], str]]] = {
    1: [
        (["金融產品", "投資服務", "國際金融中心", "監管原因", "為何監管"], "1"),
        (["財經事務", "庫務局", "行政長官", "監管當局", "金管局", "保監", "強積金"], "2"),
        (["證監會", "國際證監會", "組織架構", "風險為本", "披露為本", "評審結果", "主席", "行政總裁", "企業融資部", "中介機構科", "執法"], "3"),
        (["香港交易所", "港交所", "聯交所", "期交所", "結算所", "自動對盤"], "4"),
        (["中介人", "持牌法團", "註冊機構", "參與者", "保管人", "投資銀行"], "5"),
    ],
    2: [
        (["普通法", "衡平法", "法院", "司法", "條例", "附屬法例", "習慣法", "法律制度"], "1"),
        (["公司條例", "董事", "股東", "招股章程", "清盤", "有限公司", "特別決議", "普通決議"], "2"),
    ],
    3: [
        (["背景", "單一法例", "綜合"], "1"),
        (["導言", "釋義", "附表1"], "2"),
        (["證監會", "目標", "職能", "權力及責任"], "3"),
        (["交易所", "結算所", "交易所控制人", "投資者賠償", "自動化交易"], "4"),
        (["投資要約", "廣告", "邀請"], "5"),
        (["發牌", "註冊", "受規管活動", "第5部", "第 V 部"], "6"),
        (["財政資源", "客戶資產", "審計", "資本規定", "第6部", "第 VI 部"], "7"),
        (["業務操守", "第7部", "第 VII 部"], "8"),
        (["監管及調查", "調查", "第8部", "第 VIII 部"], "9"),
        (["紀律", "譴責", "暫時吊銷", "第9部", "第 IX 部"], "10"),
        (["干預", "限制通知", "第10部", "第 X 部"], "11"),
        (["上訴審裁處", "覆核", "第11部", "第 XI 部"], "12"),
    ],
    5: [
        (["引言", "受信", "客戶關係"], "1"),
        (
            [
                "操守準則",
                "一般原則",
                "專業投資者",
                "機構專業投資者",
                "法團專業投資者",
                "個人專業投資者",
                "風險披露",
                "客戶協議",
                "適合性",
                "認識你的客戶",
                "客戶身份",
                "帳戶",
            ],
            "2",
        ),
        (["基金經理操守"], "3"),
        (["企業融資顧問操守", "保薦人"], "4"),
        (["信貸評級", "提供信貸評級"], "5"),
        (["股份登記機構"], "6"),
    ],
    4: [
        (["發牌", "註冊", "負責人員", "持牌代表", "受規管活動", "適當人選", "大股東", "牌照", "註冊機構"], "1"),
        (["財政資源", "速動資金", "繳足股本", "資本規定"], "2"),
        (["客戶證券", "再質押", "保證金融資", "證券抵押品"], "3"),
        (["客戶款項", "獨立帳戶", "信託帳戶"], "4"),
        (["備存紀錄", "紀錄規則", "保存至少"], "5"),
        (["成交單據", "戶口結單", "收據規則"], "6"),
        (["場外衍生", "匯報", "掉期息率", "不交收遠期"], "6"),
    ],
    6: [
        (["引言"], "1"),
        (["內部監控", "管理監督", "資訊管理", "職能分隔"], "2"),
        (["洗錢", "恐怖分子", "打擊洗錢", "客戶盡職審查", "可疑交易"], "3"),
        (["電子交易", "另類交易平台", "自動對盤以外"], "4"),
        (["個人資料", "私隱"], "5"),
        (["合規", "投訴", "利益衝突"], "6"),
        (["投保", "保險", "彌償"], "7"),
    ],
    7: [
        (["導言", "交易所參與"], "1"),
        (["港交所", "香港交易及結算", "市場結構"], "2"),
        (["聯交所", "上市證券", "交易時間", "賣空", "淡倉", "中央結算", "收市競價", "市調機制"], "3"),
        (["股票期權", "期權買賣", "期權結算"], "4"),
        (["期貨", "期交所", "期貨合約"], "5"),
        (["買賣及市場推廣", "介紹", "推廣"], "6"),
    ],
    8: [
        (["上市規則", "招股", "主板", "創業板", "保薦人", "上市"], "1"),
        (["收購", "合併", "股份回購", "收購守則", "強制性要約"], "2"),
        (["認可產品", "集體投資", "單位信託", "互惠基金", "結構性產品", "ilp", "強積金"], "3"),
    ],
    9: [
        (["市場失當", "內幕交易", "虛假交易", "操控價格", "披露虛假", "操縱市場"], "1"),
        (["後果", "民事", "刑事", "市場失當行為審裁處"], "2"),
        (["未獲邀約", "造訪", "cold call", "推銷"], "3"),
        (["不當交易", "鼠倉", "前線奔跑", "搓盤"], "4"),
        (["執法", "檢控", "紀律處分"], "5"),
    ],
}


def norm(s: str) -> str:
    s = (s or "").casefold()
    s = s.replace("（", "(").replace("）", ")")
    s = s.replace("“", "").replace("”", "").replace('"', "")
    s = re.sub(r"\s+", "", s)
    return s


def question_text(q: Dict[str, Any]) -> str:
    opts = q.get("options") or {}
    opt_txt = " ".join(str(opts.get(k, "")) for k in ("A", "B", "C", "D"))
    ans = q.get("answer") or ""
    ans_txt = str(opts.get(ans, "")) if ans else ""
    return " ".join(
        [
            q.get("stem") or "",
            opt_txt,
            ans_txt,
            q.get("explanation") or "",
            q.get("chapterTitle") or "",
        ]
    )


def load_manual_index() -> Dict[int, List[Dict[str, Any]]]:
    index: Dict[int, List[Dict[str, Any]]] = {}
    for n in range(1, 10):
        ch = json.loads((MANUAL_DIR / "chapters" / f"{n:02d}.json").read_text(encoding="utf-8"))
        sections = []
        for s in ch["sections"]:
            if s["id"] in SKIP_SECTIONS:
                continue
            parts: List[str] = [s.get("title") or ""]
            for b in s.get("blocks") or []:
                if b.get("text"):
                    parts.append(b["text"])
                if b.get("caption"):
                    parts.append(b["caption"])
                if b.get("num"):
                    parts.append(str(b["num"]))
            body = "\n".join(parts)
            sections.append(
                {
                    "id": s["id"],
                    "title": re.sub(r"^\d+\s+", "", s.get("title") or s["id"]).strip()
                    or s.get("title")
                    or s["id"],
                    "rawTitle": s.get("title") or "",
                    "text": body,
                    "norm": norm(body),
                }
            )
        index[n] = sections
    return index


def score_section(qtext_n: str, section: Dict[str, Any], chapter: int) -> float:
    score = 0.0
    title_n = norm(section["rawTitle"])
    # title token hits
    for token in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9]{3,}", title_n):
        if len(token) >= 2 and token in qtext_n:
            score += 4.0 if len(token) >= 3 else 2.0

    # body keyword hits (selected distinctive terms from section text)
    # Use overlapping CJK bigrams/trigrams lightly via presence of longer title words already,
    # plus explicit topic rules below.

    for keywords, sec_id in TOPIC_RULES.get(chapter, []):
        if section["id"] != sec_id:
            continue
        for kw in keywords:
            kn = norm(kw)
            if kn and kn in qtext_n:
                score += 6.0

    # light content overlap: count distinctive 3+ char CJK chunks from title/body headers
    for m in re.findall(r"[\u4e00-\u9fff]{3,8}", section["norm"][:800]):
        if m in qtext_n:
            score += 0.35

    return score


def parse_section_field(raw: Any, chapter: int) -> Optional[Tuple[str, Optional[str]]]:
    """Parse fields like '5.2.69 & 5.2.71' or '4.5.5' → (sectionId, paragraphNum)."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    # Prefer references matching this chapter: ch.sec.para → section=sec, para=sec.para
    matches = re.findall(rf"\b{chapter}\.(\d+)\.(\d+(?:\.\d+)*)\b", text)
    if matches:
        sec, para_tail = matches[0]
        return sec, f"{sec}.{para_tail}"
    matches2 = re.findall(rf"\b{chapter}\.(\d+)\b", text)
    if matches2:
        return matches2[0], None
    if re.fullmatch(r"\d{1,2}", text):
        return text, None
    # sec.para (e.g. 2.69)
    m = re.search(r"\b(\d{1,2})\.(\d+)(?:\.(\d+))?\b", text)
    if m:
        a, b, c = m.group(1), m.group(2), m.group(3)
        if int(a) <= 20:
            paragraph = f"{a}.{b}" + (f".{c}" if c else "")
            return a, paragraph
    return None


def pick_ref(
    q: Dict[str, Any], sections: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    chapter = q.get("chapter")
    if not chapter or not sections:
        return None

    by_id = {s["id"]: s for s in sections}
    qtext = question_text(q)
    qn = norm(qtext)

    candidates: List[Tuple[float, Dict[str, Any], str, Optional[str]]] = []

    parsed = parse_section_field(q.get("section"), chapter)
    if parsed:
        sid, para = parsed
        if sid in by_id:
            candidates.append(
                (22.0 + score_section(qn, by_id[sid], chapter), by_id[sid], "meta:sectionField", para)
            )

    raw_sub = q.get("subchapter")
    if raw_sub is not None and str(raw_sub) in by_id:
        sid = str(raw_sub)
        candidates.append(
            (12.0 + score_section(qn, by_id[sid], chapter), by_id[sid], "meta:subchapter", None)
        )

    for s in sections:
        sc = score_section(qn, s, chapter)
        if sc > 0:
            candidates.append((sc, s, "score", None))

    if not candidates:
        s = sections[0]
        return {
            "chapter": chapter,
            "section": s["id"],
            "sectionTitle": s["title"],
            "label": f"第 {chapter} 章 · {s['title']}",
            "path": f"/manual/{chapter}?section={s['id']}",
            "method": "fallback",
            "confidence": "low",
        }

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best, method, para = candidates[0]

    meta = [c for c in candidates if c[2].startswith("meta:")]
    if meta:
        meta.sort(key=lambda x: x[0], reverse=True)
        if meta[0][0] >= best_score - 2:
            best_score, best, method, para = meta[0]

    confidence = "high" if best_score >= 14 else "medium" if best_score >= 7 else "low"
    path = f"/manual/{chapter}?section={best['id']}"
    label = f"第 {chapter} 章 · {best['title']}"
    paragraph: Optional[str] = None
    if para and re.match(r"^\d+\.\d+", str(para)):
        paragraph = str(para)
        path += f"&para={paragraph}"
        label += f"（{paragraph}）"

    return {
        "chapter": chapter,
        "section": best["id"],
        "sectionTitle": best["title"],
        "paragraph": paragraph,
        "label": label,
        "path": path,
        "method": method,
        "confidence": confidence,
        "score": round(best_score, 2),
    }

def main() -> None:
    bank = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    questions = bank["questions"]
    index = load_manual_index()

    refs: Dict[str, Any] = {}
    conf = Counter()
    methods = Counter()
    missing = 0

    for q in questions:
        ch = q.get("chapter")
        sections = index.get(ch) or []
        ref = pick_ref(q, sections)
        if not ref:
            missing += 1
            q.pop("manualRef", None)
            continue
        slim = {
            "chapter": ref["chapter"],
            "section": ref["section"],
            "sectionTitle": ref["sectionTitle"],
            "label": ref["label"],
            "path": ref["path"],
            "confidence": ref["confidence"],
        }
        if ref.get("paragraph"):
            slim["paragraph"] = ref["paragraph"]
        refs[q["id"]] = {**slim, "method": ref["method"], "score": ref.get("score")}
        q["manualRef"] = slim
        conf[ref["confidence"]] += 1
        methods[ref["method"]] += 1

    OUT_REFS.write_text(
        json.dumps(
            {
                "versionId": "v2.8-2016-08",
                "generatedBy": "scripts/link_questions_to_manual.py",
                "total": len(refs),
                "confidence": dict(conf),
                "methods": dict(methods),
                "refs": refs,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    QUESTIONS.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"linked {len(refs)}/{len(questions)} missing={missing}")
    print("confidence", dict(conf))
    print("methods", dict(methods))

    # sample per chapter
    by_ch = defaultdict(list)
    for qid, r in refs.items():
        by_ch[r["chapter"]].append((qid, r))
    for ch in range(1, 10):
        items = by_ch[ch][:3]
        print(f"ch{ch} samples:")
        for qid, r in items:
            print(f"  {qid} -> {r['label']} [{r['confidence']}/{r['method']}]")


if __name__ == "__main__":
    main()
