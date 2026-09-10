#!/usr/bin/env python3
"""Build data/kanji_labels.json — target-漢字 → question-bank link map.

Scope: the ENTIRE question bank of the sibling repo `jlpt-n1-question-bank`
(`past-exams/**/*.json` — 2010-07 … 2025-07 all 27 sessions, sections
語彙/文法/読解/聴解). Every 漢字 that appears anywhere in the bank (question
stems, options, correct answers, reading passages, listening transcripts) is
collected together with its paper, section, question numbers, and the public
study-material card words.

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
APP = BASE + "/index.html"
VOCAB_Q12_TYPES = {"reading", "context"}  # 問題1・問題2 (have public q-anchors)


def _vocab_pages():
    """Auto-derive the public 学習材料 pages from the sibling's built docs/
    (vocab-words.html = 2024-07 flagship, vocab-words-<session>.html for the
    other 26 sessions) so the map stays in sync with the sibling repo."""
    out = {}
    for p in sorted((SIBLING / "docs").glob("vocab-words*.html")):
        paper = p.stem[len("vocab-words"):].lstrip("-") or "2024-07"
        out[paper] = BASE + "/" + p.name
    return out


VOCAB_PAGES = _vocab_pages()
SECTION_ORDER = ["vocab", "grammar", "reading", "listening"]

_JP_READING = None

# 簡体字・OCR/フォント代替の化け（Unihan に読みが付いても実質は非日本語）
JP_EXCLUDE = set("丕仃仴别办变囫圜增壳尐异忤步气污满漯瀲烋确稍絪耴")


def jp_reading_chars():
    """Chars having a Japanese reading in Unihan (kJapaneseOn/kJapaneseKun).

    Filters out simplified-Chinese forms and OCR/フォント代替 garbles that leak
    into the bank text (处/现/连/办 …). None means the Unihan file is missing
    (then the filter is disabled)."""
    global _JP_READING
    if _JP_READING is not None:
        return _JP_READING
    path = SIBLING / "refs" / "unihan" / "Unihan_Readings.txt"
    jp = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            fld = line.split("\t")
            if len(fld) >= 2 and fld[0].startswith("U+") \
                    and fld[1] in ("kJapaneseOn", "kJapaneseKun"):
                jp.add(chr(int(fld[0][2:], 16)))
    _JP_READING = jp or None
    return _JP_READING

CJK_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")
KANA_RE = re.compile(r"[ぁ-んァ-ヶ\s]")
RUN_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFFぁ-んァ-ヶ]+")


def example_phrase(text, ch, maxlen=14):
    """例欄用: 本文中の ch を含む短い語（漢字＋送り仮名の連なり）を 1 つ返す。
    実例は OCR 化けを含むことがあるので、末尾の読点・助詞・化けを落として
    ch 中心の 6 字程度に切り詰める。無ければ ch 単体。"""
    cands = []
    for m in RUN_RE.finditer(text):
        run = m.group(0)
        pos = run.find(ch)
        if pos < 0:
            continue
        best = ch
        # 長い連なり: ch より後ろの送り仮名＋漢字を最大 5 字、手前は漢字 1 字まで
        # （が・を・に などの助詞は単語切れに見えるので手前に含めない）
        left = ""
        if pos > 0 and re.match(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]",
                                run[pos - 1]):
            left = run[pos - 1]
        if pos < len(run) - 1:
            tail = re.sub(r"[、。．・…！？\s]+$", "", run[pos + 1:pos + 6])
            cand = left + ch + tail
            best = cand if len(cand) <= maxlen else ch + tail[:maxlen - 1]
        cands.append(best)
    # 2 字以上の候補（ch 単体が手近にある場合も語を優先）、最短のものを採用
    words = [c for c in cands if len(c) >= 2]
    if words:
        return min(words, key=len)
    return ch


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
                                     "q": {}, "words": [], "example": "", "url": ""})

    # -------- vocabulary study materials (card words) --------
    # カード見出しは全27场の語彙・文法・読解材料から拾う（public #w- アンカー）。
    for p in sorted((SIBLING / "analysis").glob("*-*.md")):
        if p.name.endswith("-listening.md"):
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
        chars = question_kanji(q)
        listen_text = ""
        if sec == "listening":
            listen_text = "\n".join(
                ln for ln in (q.get("explanation") or "").splitlines()
                if KANA_RE.findall(ln) and KANA_RE.search(ln))
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
            if not e.get("example"):
                src = listen_text if sec == "listening" else (
                    (q.get("question") or "") + "".join(q.get("options") or []) + " "
                    + (q.get("answer") or ""))
                if src:
                    e["example"] = example_phrase(src, ch)
            if not e["url"]:
                # public #q<num> anchor only exists for the flagship 2024 pages
                # (old-session 問題1/2 materials are not published there)
                if (paper in ("2024-07", "2024-12")
                        and sec == "vocab" and q.get("type") in VOCAB_Q12_TYPES
                        and qnum):
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
    jp = jp_reading_chars()
    if jp is not None:
        n_drop = sum(1 for c in kanji if c not in jp or c in JP_EXCLUDE)
        kanji = {c: e for c, e in kanji.items() if c in jp and c not in JP_EXCLUDE}
    else:
        n_drop = 0
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
    if n_drop:
        print(f"dropped without Japanese reading: {n_drop}")
    print(f"unique kanji: {len(kanji)}  (links: {n_url} = {n_pub} public + {n_app} app deep-link)")
    stocks = {p: sum(1 for e in kanji.values() if p in e["papers"]) for p in
              sorted({p for e in kanji.values() for p in e["papers"]})}
    print("per paper:", stocks)
    print("sections:", {s: sum(1 for e in kanji.values() if s in e["sections"])
                        for s in SECTION_ORDER})


if __name__ == "__main__":
    main()