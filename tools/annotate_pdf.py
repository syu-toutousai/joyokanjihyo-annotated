#!/usr/bin/env python3
"""Annotate the 常用漢字表 PDF with study-material links.

Every kanji from data/kanji_labels.json that appears as a 本表 entry gets:
  - a small colored chip right of the glyph:  24·N1·問1  (2024 N1 問題 / 問)
  - a thin underline under the glyph (hyperlink hint)
  - a PDF Link annotation (URI) to the matching word card on the
    学習材料 page (vocab-words.html#w-<word>)

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
COLOR_Q1 = (0.29, 0.42, 0.95)   # 問題1 indigo
COLOR_Q2 = (0.91, 0.35, 0.05)   # 問題2 orange
COLOR_BOTH = (0.47, 0.31, 0.97)  # both purple
GAP_LEFT = 55.0     # 字形 column x window
GAP_RIGHT = 95.0
ONYX_RIGHT = 135.9  # 音 column left edge (keep chips left of it)


def label_width(label, fs):
    return pymupdf.get_text_length(label, fontname=FONT, fontsize=fs)


def chip_color(mondai):
    if mondai == [1]:
        return COLOR_Q1
    if mondai == [2]:
        return COLOR_Q2
    return COLOR_BOTH


def make_label(mondai):
    return "24·N1·" + "・".join("問%d" % m for m in mondai)


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


def chip_geom(gx0, gy0, gx1, gy1, label, fs):
    w = label_width(label, fs)
    pad = fs * 0.33
    cy = (gy0 + gy1) / 2
    ch = fs + 2 * pad
    x0 = gx1 + 2.5
    x1 = x0 + w + 2 * pad
    return x0, cy - ch / 2, x1, cy + ch / 2, w


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
        color = chip_color(info["mondai"])
        pno, (gx0, gy0, gx1, gy1) = entries[ch]
        label = make_label(info["mondai"])
        fs = 4.5
        avail = ONYX_RIGHT - (gx1 + 2.5) - 2.0
        if label_width(label, fs) + 2 * fs * 0.33 > avail:
            label = "N1·" + "・".join("問%d" % m for m in info["mondai"])
            while label_width(label, fs) + 2 * fs * 0.33 > avail and fs > 3.0:
                fs -= 0.5
        cx0, cy0, cx1, cy1, w = chip_geom(gx0, gy0, gx1, gy1, label, fs)
        page = doc[pno]
        page.draw_rect(pymupdf.Rect(cx0, cy0, cx1, cy1),
                       color=color, fill=color, radius=0.35, width=0)
        page.insert_text((cx0 + (cx1 - cx0 - w) / 2, (cy0 + cy1) / 2 + fs * 0.34),
                         label, fontname=FONT, fontsize=fs, color=(1, 1, 1))
        page.draw_line(pymupdf.Point(gx0 - 1.5, gy1 + 0.9),
                       pymupdf.Point(gx1 + 1.5, gy1 + 0.9),
                       color=color, width=1.15)
        link_rect = pymupdf.Rect(gx0 - 1.5, gy0 - 1.5, max(gx1 + 1.5, cx1), gy1 + 1.5)
        page.insert_link({"kind": pymupdf.LINK_URI, "from": link_rect, "uri": info["url"]})
        placed += 1
        stats.append((ch, pno + 1, gx0, gy0, label, info["url"]))
    doc.save(OUT, garbage=3, deflate=True)
    print(f"annotated: {placed} of {len(LABELS)} kanji")
    if missing:
        print("NOT FOUND (skipped):", " ".join(missing))
    for ch, pno, x, y, label, url in stats:
        print(f"  {ch}  page {pno:>3}  ({x:.1f},{y:.1f})  [{label}]  {url}")


if __name__ == "__main__":
    sys.exit(main())