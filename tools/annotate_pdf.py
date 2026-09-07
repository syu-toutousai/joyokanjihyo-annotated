#!/usr/bin/env python3
"""Annotate the 常用漢字表 PDF with study-material links.

Every kanji from data/kanji_labels.json that appears as a 本表 entry gets a
small icon cluster placed in the whitespace band directly ABOVE the glyph
(at the top edge of the 字形 cell), so it never overlaps the kanji entry or
the 音/訓/例 columns that follow it:

    ┌────┐
    │ 20 │   ( )   (①)
    │ 24 │    N1
    └────┘
                    ← the icon cluster, then
      腐           ← the 字形 column
      ホ　フ　...   ← 音/訓 column (never covered)

Icons per element (colour-coded, 一目):
  - 2024  → small navy rectangle "20 / 24"
  - N1    → red circle
  - 問     → filled circle in the 問 colour carrying ①/② (①=問題1 indigo,
              ②=問題2 orange; both are shown when the kanji appears in both)

The glyph and the icon cluster are wrapped in one PDF Link annotation
pointing at the matching word card: vocab-words.html#w-<word>

Output: src/joyokanjihyo_20101130_annotated.pdf
"""
import json
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "joyokanjihyo_20101130.pdf"
OUT = ROOT / "src" / "joyokanjihyo_20101130_annotated.pdf"
LABELS = json.loads((ROOT / "data" / "kanji_labels.json").read_text(encoding="utf-8"))

FONT = "china-s"
NAVY = (0.10, 0.18, 0.46)       # 2024 rectangle
RED = (0.85, 0.13, 0.12)        # N1 circle
COLOR_Q1 = (0.29, 0.42, 0.95)   # 問題1 ①
COLOR_Q2 = (0.91, 0.35, 0.05)   # 問題2 ②
ON_CIRCLE = {1: "①", 2: "②"}

GAP_LEFT = 55.0     # 字形 column x window
GAP_RIGHT = 95.0
ICON_H = 7.5        # icon band height (fits the 8.5pt whitespace above a glyph)
BAND_GAP = 1.0      # whitespace between band bottom and glyph top
ICON_GAP = 1.2      # horizontal gap between icons
YEAR_FS = 3.0
N1_FS = 2.7
CIR_FS = 4.5


def tw(text, fs):
    return pymupdf.get_text_length(text, fontname=FONT, fontsize=fs)


def icon_blocks(info):
    """Return list of (kind, payload) icon specs for a kanji entry."""
    blocks = [("year", None), ("n1", None)]
    for m in info["mondai"]:  # ① then ②
        blocks.append(("sai", m))
    return blocks


def size_of(blocks):
    """widths/heights for the icon cluster."""
    sizes = []
    for kind, extra in blocks:
        if kind == "year":
            sizes.append(("year", max(tw("20", YEAR_FS), tw("24", YEAR_FS)) + 1.4, ICON_H))
        elif kind == "n1":
            sizes.append(("n1", ICON_H, ICON_H))
        else:
            sizes.append(("sai", ICON_H - 0.5, ICON_H - 0.5))
    w = sum(s[1] for s in sizes) + ICON_GAP * (len(sizes) - 1)
    return sizes, w


def draw_cluster(page, x, ytop, blocks, colors):
    """Draw the icon cluster at x (left), top y; return right edge."""
    cxs = []
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
            c = COLOR_Q1 if extra == 1 else COLOR_Q2
            d = ICON_H - 0.5
            cx = xcur + d / 2
            cy = ytop + d / 2
            page.draw_circle(pymupdf.Point(cx, cy), d / 2, color=c, fill=c, width=0)
            page.insert_text((cx - tw(ON_CIRCLE[extra], CIR_FS) / 2, cy + CIR_FS * 0.35),
                             ON_CIRCLE[extra], fontname=FONT, fontsize=CIR_FS, color=(1, 1, 1))
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
        end_x = draw_cluster(page, start_x, ytop, blocks, info["mondai"])
        link_rect = pymupdf.Rect(start_x - 1.5, gy0 - BAND_GAP - ICON_H - 0.5,
                                 max(gx1 + 1.5, end_x + 1.5), gy1 + 1.5)
        page.insert_link({"kind": pymupdf.LINK_URI, "from": link_rect, "uri": info["url"]})
        placed += 1
        stats.append((ch, pno + 1, start_x, ytop, info["mondai"], info["url"]))
    doc.save(OUT, garbage=3, deflate=True)
    print(f"annotated: {placed} of {len(LABELS)} kanji")
    if missing:
        print("NOT FOUND (skipped):", " ".join(missing))
    for ch, pno, x, y, mondai, url in stats:
        print(f"  {ch}  page {pno:>3}  icons@({x:.1f},{y:.1f})  mondai={mondai}\t{url}")


if __name__ == "__main__":
    sys.exit(main())