#!/usr/bin/env python3
"""Annotate the 常用漢字表 PDF with question-bank links.

Every kanji from data/kanji_labels.json that appears as a 本表 entry gets a
small icon cluster placed in the whitespace band directly ABOVE the glyph
(at the top edge of the 字形 cell), so it never overlaps the kanji entry or
the 音/訓/例 columns that follow it:

    ┌────┐
    │ 20 │  N1 (語)(文)(読)(聴)
    │ 24 │
    └────┘
                     ← the icon cluster, then
       腐            ← the 字形 column
       ホ　フ　...    ← 音/訓 column (never covered)

Icons per element (colour-coded, 一目):
  - 2024  → small navy rectangle "20 / 24"  (出題年度)
  - N1    → red circle
  - 題種  → one filled circle per exam section the kanji appeared in, in the
            question-bank site's section colours, carrying the letter
            語 / 文 / 読 / 聴 (語彙, 文法, 読解, 聴解)

The glyph and the icon cluster are wrapped in one PDF Link annotation:
  - kanji that is a 語彙カード word  → the public 学習材料 page:                        vocab-words*.html#w-<word>
  - 語彙 問題1/2 (q1..q13)           → the public 学習材料 question anchor:            vocab-words*.html#q<num>
  - everything else (文法/読解/聴解) → deep link into the encrypted question bank:     index.html#q=<question-id>

Besides the badge pass, two more annotation kinds are produced:

  - HIGHLIGHT pass: 教材の語が本表の「音・訓・例・備考」欄にも現れている場合、
    その語をマーカー色で塗りつぶし、語彙カードへリンクする。

  - APPENDIX (付録): 常用漢字表に収録されない表外漢字（教材に現れたもの）は、
    本表と同じ体裁（字形・音・訓・例・備考）の行を末尾の新ページに追加し、
    本表と同じくアイコン群＋リンクを付す。読みは Unihan のkJapaneseOn/kun による。

Output: src/joyokanjihyo_20101130_annotated.pdf
"""
import collections
import json
import re
from pathlib import Path
from urllib.parse import quote

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "joyokanjihyo_20101130.pdf"
OUT = ROOT / "src" / "joyokanjihyo_20101130_annotated.pdf"
LABELS = json.loads((ROOT / "data" / "kanji_labels.json").read_text(encoding="utf-8"))

BASE = "https://syu-toutousai.github.io/jlpt-n1-question-bank"
VOCAB_PAGES = {"2024-07": BASE + "/vocab-words.html",
               "2024-12": BASE + "/vocab-words-2024-12.html"}

FONT = "china-s"
NAVY = (0.10, 0.18, 0.46)       # 2024 rectangle
RED = (0.85, 0.13, 0.12)        # N1 circle
SEC_LABEL = {"vocab": "語", "grammar": "文", "reading": "読", "listening": "聴"}
SEC_COLOR = {"vocab": (0.91, 0.35, 0.05),   # matches the question-bank site
             "grammar": (0.18, 0.62, 0.27),
             "reading": (0.10, 0.44, 0.76),
             "listening": (0.88, 0.19, 0.19)}
MARK = (0.98, 0.86, 0.28)       # 語のハイライト色（マーカー）

GAP_LEFT = 55.0     # 字形 column x window
GAP_RIGHT = 95.0
ICON_H = 7.5        # icon band height (fits the 8.5pt whitespace above a glyph)
BAND_GAP = 1.0      # whitespace between band bottom and glyph top
ICON_GAP = 1.2      # horizontal gap between icons
YEAR_FS = 3.0
N1_FS = 2.7
SEC_FS = 3.4

# 付録（表外漢字）ページの体裁 —— 本表の列配置（音=135.9 / 例=209.9）に揃える
APP_X0 = 50.0
APP_X1 = 135.9      # 字形 / 音
APP_X2 = 209.9      # 音 / 例
APP_X3 = 311.0      # 例 / 備考
ROW_H = 36.0
# 表外漢字: (音, 訓, 例, 備考) — 音・訓は Unihan 8.0 kJapaneseOn/kJapaneseKun。
# 例は問題バンクでの実際の語（教材語）に揃える。
EXTRA = {
    "咎": ("キュウ", "　とが・める　とが", "咎める，責咎", "常用漢字表外"),
    "脆": ("ゼイ", "　もろ・い", "脆い，脆弱", "常用漢字表外"),
    "填": ("テン・チン", "　うず・める　ふさぐ", "補填，填まる", "常用漢字表外"),
    "惹": ("ジャ・ジャク", "　ひく", "注意を惹く（関心を惹いた）", "常用漢字表外"),
    "捷": ("ショウ・ソウ", "　はやい", "敏捷，捷(注)", "常用漢字表外"),
    "揃": ("セン", "　そろ・う　そろ・える　そろい", "揃う（揃ったら）", "常用漢字表外"),
    "揉": ("ジュウ", "　もむ", "揉める（揉めてて）", "常用漢字表外"),
    "撫": ("ブ・フ", "　なでる", "撫でる（撫で続け）", "常用漢字表外"),
    "斂": ("レン", "　おさめる", "収斂（収斂進化）", "常用漢字表外"),
    "歪": ("ワイ", "　ゆがむ　ひずむ", "歪む（歪んでしまった）", "常用漢字表外"),
    "汲": ("キュウ", "　くむ", "汲む（意を汲み）", "常用漢字表外"),
    "淘": ("トウ", "　よな・げる", "淘汰(注)", "常用漢字表外"),
    "澤": ("タク", "　さわ", "澤田（人物名）", "常用漢字表外・沢の旧字形"),
    "爬": ("ハ", "（訓なし）", "爬虫類", "常用漢字表外"),
    "繋": ("ケイ", "　つなぐ　かける", "繋がる，繋ぎ合わ", "常用漢字表外・繋の俗字"),
    "罠": ("ビン・ミン", "　わな", "罠", "常用漢字表外"),
    "茸": ("ジョウ", "　きのこ　たけ", "茸，山菜も茸も", "常用漢字表外"),
    "蒔": ("シ・ジ", "　まく　うえる", "蒔く（種を蒔く）", "常用漢字表外"),
    "辭": ("ジ・シ", "（訓なし）", "辭言（問題バンク語）", "常用漢字表外・辞の旧字形"),
    "辿": ("テン", "　たど・る　たどり", "辿り着く（辿り着けない）", "常用漢字表外"),
    "迂": ("ウ", "（訓なし）", "迂闊（迂闊さ）", "常用漢字表外"),
    "闊": ("カツ", "　ひろ・い", "迂闊(注)", "常用漢字表外"),
    "馴": ("シュン・クン", "　なれ・る　なら・す", "馴れる（馴れてくる）", "常用漢字表外"),
}


def tw(text, fs):
    return pymupdf.get_text_length(text, fontname=FONT, fontsize=fs)


def icon_blocks(info):
    """Return list of (kind, payload) icon specs for a kanji entry."""
    blocks = [("year", None), ("n1", None)]
    for sec in info["sections"]:
        blocks.append(("sec", sec))
    return blocks


def size_of(blocks):
    sizes = []
    for kind, extra in blocks:
        if kind == "year":
            sizes.append(("year", max(tw("20", YEAR_FS), tw("24", YEAR_FS)) + 1.4, ICON_H))
        elif kind == "n1":
            sizes.append(("n1", ICON_H, ICON_H))
        else:
            sizes.append(("sec", ICON_H, ICON_H))
    w = sum(s[1] for s in sizes) + ICON_GAP * (len(sizes) - 1)
    return sizes, w


def draw_cluster(page, x, ytop, blocks):
    """Draw the icon cluster at x (left), top y; return right edge."""
    xcur = x
    for kind, extra in blocks:
        if kind == "year":
            rect = pymupdf.Rect(xcur, ytop, xcur + max(tw("20", YEAR_FS), tw("24", YEAR_FS)) + 1.4,
                                ytop + ICON_H)
            page.draw_rect(rect, color=NAVY, fill=NAVY, width=0)
            for line, txt in ((1, "20"), (2, "24")):
                baseline = rect.y0 + line * YEAR_FS + 0.5
                page.insert_text((rect.x0 + (rect.width - tw(txt, YEAR_FS)) / 2, baseline),
                                 txt, fontname=FONT, fontsize=YEAR_FS, color=(1, 1, 1))
            xcur = rect.x1
        elif kind == "n1":
            d = ICON_H
            cx = xcur + d / 2
            cy = ytop + d / 2
            page.draw_circle(pymupdf.Point(cx, cy), d / 2, color=RED, fill=RED, width=0)
            page.insert_text((cx - tw("N1", N1_FS) / 2, cy + N1_FS * 0.35),
                             "N1", fontname=FONT, fontsize=N1_FS, color=(1, 1, 1))
            xcur += d
        else:
            d = ICON_H
            cx = xcur + d / 2
            cy = ytop + d / 2
            page.draw_circle(pymupdf.Point(cx, cy), d / 2,
                             color=SEC_COLOR[extra], fill=SEC_COLOR[extra], width=0)
            page.insert_text((cx - tw(SEC_LABEL[extra], SEC_FS) / 2, cy + SEC_FS * 0.35),
                             SEC_LABEL[extra], fontname=FONT, fontsize=SEC_FS, color=(1, 1, 1))
            xcur += d
        xcur += ICON_GAP
    return xcur - ICON_GAP


def find_entries(doc):
    """char -> (page_index, glyph_bbox) across the 本表."""
    targets = set(LABELS)
    entries = {}
    for pno in range(10, len(doc)):  # 本表 only — skip 字体解説 sample pages 0-9
        rd = doc[pno].get_text("rawdict")
        for b in rd["blocks"]:
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    if s["size"] < 15:
                        continue
                    for c in s.get("chars", []):
                        ch = c["c"].strip()
                        if len(ch) != 1 or ch not in targets:
                            continue
                        x0, y0, x1, y1 = c["bbox"]
                        if not (GAP_LEFT <= x0 <= GAP_RIGHT):
                            continue
                        if ch not in entries:
                            entries[ch] = (pno, tuple(round(v, 1) for v in c["bbox"]))
    return entries


def highlight_words(doc):
    """教材で拾った語が本表の音・訓・例・備考欄にも現れていればマーカー色で
    塗り、語彙カードへリンクする。字形欄（x<120）は対象外。
    Returns number of highlighted occurrences."""
    words = []
    for v in LABELS.values():
        for m in v["words"]:
            w = m["w"]
            if all(not (x["w"] == w and x["page"] == m["page"]) for x in words):
                words.append(m)
    words.sort(key=lambda m: len(m["w"]), reverse=True)
    hits = 0
    for pno in range(10, 161):  # 本表（ページ11〜161）
        page = doc[pno]
        rd = page.get_text("rawdict")
        base = collections.defaultdict(list)
        for b in rd["blocks"]:
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    for c in s.get("chars", []):
                        if c["c"].strip():
                            base[round(c["bbox"][1], 1)].append((c["c"], tuple(c["bbox"])))
        for arr in base.values():
            arr.sort(key=lambda t: t[1][0])
            line = "".join(c for c, _ in arr)
            for m in words:
                w = m["w"]
                start = 0
                while True:
                    i = line.find(w, start)
                    if i < 0:
                        break
                    chunk = arr[i:i + len(w)]
                    ok = (len(chunk) == len(w)
                          and all(t[1][0] >= 120 for t in chunk)
                          and all(abs(chunk[k][1][0] - chunk[k - 1][1][2]) < 3.5
                                  for k in range(1, len(chunk))))
                    if ok:
                        x0, y0, _, _ = chunk[0][1]
                        _, _, x1, y1 = chunk[-1][1]
                        rect = pymupdf.Rect(x0 - 0.6, y0 - 0.6, x1 + 0.6, y1 + 0.6)
                        ha = page.add_highlight_annot([rect])
                        ha.set_colors(stroke=MARK)
                        ha.set_opacity(0.55)
                        ha.update()
                        page.insert_link({"kind": pymupdf.LINK_URI,
                                          "from": rect + pymupdf.Rect(-1, -1, 1, 1),
                                          "uri": VOCAB_PAGES[m["page"]] + quote(m["anchor"],
                                                                                safe="")})
                        hits += 1
                    start = i + 1
    return hits


def draw_appendix_header(page, y):
    page.draw_line((APP_X0, y - 10), (APP_X3, y - 10))
    page.insert_text((APP_X0 + 6, y), "漢字", fontname=FONT, fontsize=10.5)
    page.insert_text((APP_X1 + 4, y), "音", fontname=FONT, fontsize=10.5)
    page.insert_text((APP_X2 + 4, y), "訓", fontname=FONT, fontsize=10.5)
    page.insert_text((APP_X3 + 4, y), "例", fontname=FONT, fontsize=10.5)
    page.insert_text((APP_X3 + 60, y), "備考", fontname=FONT, fontsize=10.5)
    for x in (APP_X0, APP_X1, APP_X2, APP_X3):
        page.draw_line((x, y - 10), (x, 800))
    page.draw_line((APP_X0, 800), (APP_X3, 800))


def add_appendix(doc, missing):
    """表外漢字を本表風の行として末尾に追記（必要なら新ページ追加）。
    Returns (page_count, char list)."""
    if not missing:
        return 0, []
    W, H = doc[0].rect.width, doc[0].rect.height
    page = doc.new_page(width=W, height=H)
    page.insert_text((APP_X0, 40), "付録　問題バンクに現れる常用漢字表外の漢字",
                     fontname=FONT, fontsize=16)
    page.insert_text((APP_X0, 58),
                     "常用漢字表（平成22年内閣告示第二号）に収録されないが問題バンク（2024年7月・12月）"
                     "の題文・選択肢・聴解原文に現れる文字。"
                     "本表と同じ体裁で示し、アイコン・リンクも同様に付す。",
                     fontname=FONT, fontsize=9)
    page.insert_text((APP_X0, 72),
                     "音・訓は Unihan 8.0 の kJapaneseOn / kJapaneseKun、例は問題バンクでの実例。",
                     fontname=FONT, fontsize=9)
    pages = 1
    y = 92.0
    draw_appendix_header(page, y)
    y += 8
    for ch in sorted(missing):
        info = LABELS[ch]
        if y + ROW_H > H - 50:
            page = doc.new_page(width=W, height=H)
            pages += 1
            draw_appendix_header(page, 84.0)
            y = 92.0
        blocks = icon_blocks(info)
        sizes, cw = size_of(blocks)
        gcx = (APP_X0 + APP_X1) / 2
        start_x = gcx - cw / 2
        band_top = y - 1.0 - ICON_H
        draw_cluster(page, start_x, band_top, blocks)
        gw = tw(ch, 18)
        page.insert_text((gcx - gw / 2, y + 15), ch, fontname=FONT, fontsize=18)
        on, kun, rei, biko = EXTRA.get(
            ch, ("", "", info["words"][0]["w"] if info["words"] else ch, "常用漢字表外"))
        page.insert_text((APP_X1 + 4, y + 8), on, fontname=FONT, fontsize=10.5)
        page.insert_text((APP_X1 + 4, y + 21), kun, fontname=FONT, fontsize=10.5)
        page.insert_text((APP_X2 + 4, y + 8), rei, fontname=FONT, fontsize=10.5)
        page.insert_text((APP_X3 + 4, y + 8), biko, fontname=FONT, fontsize=9)
        link_rect = pymupdf.Rect(APP_X0 - 2, band_top - 1, APP_X3 + 6, y + 25)
        page.insert_link({"kind": pymupdf.LINK_URI, "from": link_rect, "uri": info["url"]})
        y += ROW_H
    return pages, sorted(missing)


def main():
    doc = pymupdf.open(SRC)
    entries = find_entries(doc)
    missing, placed = [], 0
    stats = []
    for ch in sorted(LABELS):
        if ch not in entries:
            missing.append(ch)
            continue
        info = LABELS[ch]
        pno, (gx0, gy0, gx1, gy1) = entries[ch]
        blocks = icon_blocks(info)
        sizes, cw = size_of(blocks)
        cx = (gx0 + gx1) / 2
        start_x = cx - cw / 2
        ytop = gy0 - BAND_GAP - ICON_H
        page = doc[pno]
        end_x = draw_cluster(page, start_x, ytop, blocks)
        link_rect = pymupdf.Rect(start_x - 1.5, gy0 - BAND_GAP - ICON_H - 0.5,
                                 max(gx1 + 1.5, end_x + 1.5), gy1 + 1.5)
        page.insert_link({"kind": pymupdf.LINK_URI, "from": link_rect, "uri": info["url"]})
        placed += 1
        stats.append((ch, pno + 1, "".join(SEC_LABEL[s] for s in info["sections"]), info["url"]))
    hits = highlight_words(doc)
    app_pages, app_chars = add_appendix(doc, missing)
    doc.save(OUT, garbage=3, deflate=True)
    print(f"annotated: {placed} of {len(LABELS)} kanji")
    if missing:
        print("NOT FOUND in 本表 → appendix:", " ".join(missing))
    print(f"highlighted word occurrences: {hits}")
    print(f"appendix: {len(app_chars)} kanji on {app_pages} page(s); total pages now {len(doc)}")
    for ch, pno, secs, url in stats:
        print(f"  {ch}  page {pno:>3}  sections={secs}\t{url}")


if __name__ == "__main__":
    main()