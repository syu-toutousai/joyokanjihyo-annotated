#!/usr/bin/env python3
"""Build data/kanji_labels.json — target-漢字 → study-material link map.

Reads the JLPT N1 vocabulary study markdown (analysis/2024-07-vocab-*.md of
the sibling repo jlpt-n1-question-bank), collects every card word (正解 +
干扰项) and its exam block (問題1/問題2) and question number, then expands the
words into the individual kanji composing them.

Output: data/kanji_labels.json
    kanji -> {"mondai": sorted list of 問 numbers,
              "q": sorted question numbers seen,
              "words": [word, ...],
              "url": first word's card anchor on the 学習材料 page}
"""
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MATERIALS = [
    ("analysis/2024-07-vocab-reading-words.md", 1),
    ("analysis/2024-07-vocab-context-words.md", 2),
]
SIBLING = Path(os.environ.get(
    "JLPT_QB_ROOT", Path(__file__).resolve().parents[2] / "jlpt-n1-question-bank"))
PAGE = "https://syu-toutousai.github.io/jlpt-n1-question-bank/vocab-words.html"

CJK_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")
SPECIAL_H2 = ("题干速览", "干扰项一览", "干扰项")


def parse_md(path, mondai):
    """Return list of (word, qnum) for each card in a material file."""
    cards = []
    q = 0
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("## "):
            title = line[3:]
            if not title.startswith(SPECIAL_H2):
                q += 1  # a question stem
            continue
        if not line.startswith("### "):
            continue
        t = line[4:]
        if t.startswith("【干扰项】"):
            continue  # divider, not a card
        word = re.match(r"(.+?)（", t)
        word = word.group(1) if word and "（" in t else t.rstrip("　干扰项")
        if not word or "　" in word:
            continue
        cards.append((word, q))
    return cards


def main():
    kanji = {}  # char -> {"mondai":set, "q":set, "words":[], "url":str}
    card_chars = set()
    for rel, mondai in MATERIALS:
        p = SIBLING / rel
        if not p.exists():
            print("!! missing material:", p)
            continue
        for word, q in parse_md(p, mondai):
            if not q:
                continue
            for ch in set(CJK_RE.findall(word)):
                card_chars.add(ch)
                e = kanji.setdefault(ch, {"mondai": [], "q": [], "words": [], "url": ""})
                if mondai not in e["mondai"]:
                    e["mondai"].append(mondai)
                if q not in e["q"]:
                    e["q"].append(q)
                if word not in e["words"]:
                    e["words"].append(word)
    qfile = ROOT / "data" / "questions.json"
    if qfile.exists():
        for q in json.loads(qfile.read_text(encoding="utf-8")):
            text = q["stem"] + "".join(q["options"])
            for ch in set(CJK_RE.findall(text)):
                e = kanji.setdefault(ch, {"mondai": [], "q": [], "words": [], "url": ""})
                if q["mondai"] not in e["mondai"]:
                    e["mondai"].append(q["mondai"])
                if q["q"] not in e["q"]:
                    e["q"].append(q["q"])
                if ch not in card_chars and not e["url"]:
                    e["url"] = PAGE + "#q%d" % q["q"]
                if q["answer"] not in e["words"]:
                    e["words"].append(q["answer"])
    for e in kanji.values():
        e["mondai"].sort()
        e["q"].sort()
        if not e["url"]:
            first = e["words"][0]
            e["url"] = PAGE + "#w-" + urllib.parse.quote(first)
    out = ROOT / "data" / "kanji_labels.json"
    out.write_text(json.dumps(
        {k: kanji[k] for k in sorted(kanji)}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    plain = len(kanji)
    with_link = sum(1 for e in kanji.values() if e["url"])
    print(f"source: {SIBLING}")
    print(f"unique kanji: {plain} ({with_link} with card link)")
    for ch in sorted(kanji):
        e = kanji[ch]
        print(f"  {ch}  問{''.join(map(str, e['mondai']))}  Q{','.join(map(str, e['q']))}  "
              f"{','.join(e['words'])}")


if __name__ == "__main__":
    sys.exit(main())