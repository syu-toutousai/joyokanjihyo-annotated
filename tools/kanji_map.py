#!/usr/bin/env python3
"""Build data/kanji_labels.json — target-漢字 → question-bank link map.

Scope: the ENTIRE question bank of the sibling repo `jlpt-n1-question-bank`
(`past-exams/**/*.json` — 2024-07 + 2024-12, all sections 語彙/文法/読解/聴解).
Every 漢字 that appears anywhere in the bank (question stems, options, correct
answers, reading passages, listening transcripts) is collected together with
its paper, section, question numbers, and the public study-material card words.

Link priority (one URL per entry, the rest stays as data):
  1. a 語彙カード word on a public page   → vocab-words*.html#w-<card>
  2. a 語彙 問題1/2 (q1..q13) question    → vocab-words*.html#q<num>
  3. anything else (文法/読解/聴解)        → encrypted app deep link
                                            index.html#q=<question-id>

Output: data/kanji_labels.json
    kanji -> {"papers": [...], "sections": [...], "q": {paper: [nums]},
              "words": [{"w","page","anchor"}, ...], "url": str}
"""
import json
import os
import re
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIBLING = Path(os.environ.get(
    "JLPT_QB_ROOT", Path(__file__).resolve().parents[2] / "jlpt-n1-question-bank"))
BASE = "https://syu-toutousai.github.io/jlpt-n1-question-bank"
VOCAB_PAGES = {"2024-07": BASE + "/vocab-words.html",
               "2024-12": BASE + "/vocab-words-2024-12.html"}
APP = BASE + "/index.html"
VOCAB_Q12_TYPES = {"reading", "context"}  # 問題1・問題2 (have public q-anchors)
SECTION_ORDER = ["vocab", "grammar", "reading", "listening"]

CJK_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")
KANA_RE = re.compile(r"[ぁ-んァ-ヶ\s]")


def bank_questions():
    """All question dicts from past-exams/, deduped by id, sorted by id."""
    seen = {}
    for path in sorted((SIBLING / "past-exams").rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for q in (data if isinstance(data, list) else [data]):
            if isinstance(q, dict) and q.get("id"):
                seen.setdefault(q["id"], q)
    return [seen[k] for k in sorted(seen)]


def transcript_kanji(question):
    """聴解: the spoken script lives in `explanation`. Keep only lines that are
    real Japanese. A kana-line test alone leaks Chinese translations that embed
    Japanese words/names, so require kana density > 40% of written chars."""
    out = set()
    for line in (question.get("explanation") or "").splitlines():
        kana = len(KANA_RE.findall(line))
        cjk = len(CJK_RE.findall(line))
        if kana and kana / max(1, kana + cjk) >= 0.4:
            out |= set(CJK_RE.findall(line))
    return out


def question_kanji(question):
    """Kanji from stem + options + answer (written sections)."""
    text = (question.get("question") or "") + "".join(question.get("options") or [])
    text += " " + (question.get("answer") or "")
    return set(CJK_RE.findall(text))


def vocab_card_anchors():
    """word -> {"page": year, "anchor": "#w-<id>"} from the BUILT pages.

    The card anchor ids are the ones actually live (some carry a trailing
    '　★'; some are aliases). `data-w` is the canonical word key, so we read
    that from the HTML and match md word → (data-w, id).
    """
    out = {}
    for year, url in VOCAB_PAGES.items():
        fn = url.rsplit("/", 1)[-1]
        p = SIBLING / "docs" / fn
        if not p.exists():
            continue
        html = p.read_text(encoding="utf-8")
        for m in re.finditer(r'<details class="card" id="w-([^"]+)" data-w="([^"]*)"', html):
            key, sid = m.group(2), m.group(1)
            out.setdefault(key, {"page": year, "anchor": "#w-" + sid})
            # 'とっさに　★' style data-w may exist next to plain 'とっさに'
            plain = key.replace("　★", "")
            if plain and plain not in out:
                out[plain] = {"page": year, "anchor": "#w-" + sid}
    return out


def main():
    anchors = vocab_card_anchors()
    kanji = {}

    def ensure(ch):
        return kanji.setdefault(ch, {"papers": [], "sections": [],
                                     "q": {}, "words": [], "url": ""})

    # -------- vocabulary study materials (card words) --------
    for rel in ("analysis/2024-07-vocab-reading-words.md",
                "analysis/2024-07-vocab-context-words.md",
                "analysis/2024-12-vocab-context-words.md"):
        p = SIBLING / rel
        if not p.exists():
            continue
        for line in open(p, encoding="utf-8"):
            if not line.startswith("### "):
                continue
            if line.startswith("### 【干扰项】"):
                continue
            t = line[4:].strip()
            word = re.match(r"(.+?)（", t)
            word = word.group(1) if word else t
            if not word or "　" in word:
                continue
            a = anchors.get(word) or anchors.get(word + "　★")
            if a is None:
                continue
            for ch in set(CJK_RE.findall(word)):
                e = ensure(ch)
                if a["page"] not in e["papers"]:
                    e["papers"].append(a["page"])
                if "vocab" not in e["sections"]:
                    e["sections"].append("vocab")
                if not any(x["w"] == word for x in e["words"]):
                    e["words"].append({"w": word, "page": a["page"], "anchor": a["anchor"]})
                if not e["url"]:
                    e["url"] = VOCAB_PAGES[a["page"]] + a["anchor"]

    # -------- whole question bank --------
    for q in bank_questions():
        qid = q["id"]
        m = re.match(r"^(\d{4})-(\d{2})-", qid)
        if not m or m.group(2) not in ("07", "12"):
            continue
        paper = m.group(1) + "-" + m.group(2)
        sec = q.get("section", "?")
        if qid < "2024-07" or not (2024 <= int(m.group(1))):
            pass
        chars = question_kanji(q)
        if sec == "listening":
            chars |= transcript_kanji(q)
        if not chars:
            continue
        qnum = int(q.get("number", 0))
        for ch in chars:
            e = ensure(ch)
            if paper not in e["papers"]:
                e["papers"].append(paper)
            if sec not in e["sections"]:
                e["sections"].append(sec)
            qs = e["q"].setdefault(paper, [])
            if qnum and qnum not in qs:
                qs.append(qnum)
            if not e["url"]:
                if sec == "vocab" and q.get("type") in VOCAB_Q12_TYPES and qnum:
                    e["url"] = VOCAB_PAGES[paper] + "#q%d" % qnum
                else:
                    e["url"] = APP + "#q=" + qid

    # -------- finalize --------
    for ch, e in kanji.items():
        # 語彙 問題1/2 (q<=13) has a public anchor — prefer it over the deep link
        if e["url"].startswith(APP + "#q="):
            for paper in ("2024-07", "2024-12"):
                q12 = [n for n in e["q"].get(paper, []) if n <= 13]
                if q12:
                    e["url"] = VOCAB_PAGES[paper] + "#q%d" % min(q12)
                    break
        e["papers"].sort()
        e["sections"] = [s for s in SECTION_ORDER if s in e["sections"]]
        e["q"] = {p: sorted(v) for p, v in sorted(e["q"].items())}
    out = ROOT / "data" / "kanji_labels.json"
    out.write_text(json.dumps(kanji, ensure_ascii=False, indent=1), encoding="utf-8")
    n_url = n_app = n_pub = 0
    for e in kanji.values():
        if e["url"]:
            n_url += 1
            if "index.html#q=" in e["url"]:
                n_app += 1
            else:
                n_pub += 1
    print(f"source: {SIBLING}")
    print(f"unique kanji: {len(kanji)}  (links: {n_url} = {n_pub} public + {n_app} app deep-link)")
    stocks = {p: sum(1 for e in kanji.values() if p in e["papers"]) for p in
              sorted({p for e in kanji.values() for p in e["papers"]})}
    print("per paper:", stocks)
    print("sections:", {s: sum(1 for e in kanji.values() if s in e["sections"])
                        for s in SECTION_ORDER})


if __name__ == "__main__":
    main()