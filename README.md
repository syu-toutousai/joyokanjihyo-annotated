# 常用漢字表 — JLPT N1 学習リンク版

An an `常用漢字表`（平成22年内閣告示第2号）student edition. Every 漢字 that
appears in our JLPT N1 2024 vocabulary study material is marked on its
`常用漢字表` entry with a **small badge** (`24·N1·問1`) and is **hyperlinked**
to the corresponding word card on the 学習材料 page of the
[`jlpt-n1-question-bank`](https://github.com/syu-toutousai/jlpt-n1-question-bank)
repository.

Badge colour = exam block:

| colour | meaning |
| ------ | ------- |
| indigo   | word appears in 問題1 (語彙・文法 reading) |
| orange   | word appears in 問題2 (語彙・文法 context) |
| purple   | word appears in both 問題1 and 問題2 |

Clicking any kanji (or its badge) jumps to the word card in the 学習材料:

`vocab-words.html#w-<word>`

## Files

| file | description |
| ---- | ----------- |
| `src/joyokanjihyo_20101130.pdf` | original official PDF (unchanged) |
| `src/joyokanjihyo_20101130_annotated.pdf` | our annotated edition (badges + links) |
| `tools/kanji_map.py` | extracts 漢字 → 問/link map from the study material |
| `tools/annotate_pdf.py` | draws badges + link annotations onto the PDF |
| `data/kanji_labels.json` | kanji → {問, Q, words, url} generated map |

## Why two features are skipped for some kanji

- 咎・脆 come from 2024 N1 words but are **outside** the `常用漢字表`
  (表外漢字), so they have no entry to badge. They are reported by
  `tools/annotate_pdf.py` as "NOT FOUND (skipped)".

## Rebuilding

```sh
python3 -m venv .venv && .venv/bin/pip install pymupdf
.venv/bin/python tools/kanji_map.py      # needs the sibling repo checked out
.venv/bin/python tools/annotate_pdf.py
```

`tools/kanji_map.py` reads the sibling `jlpt-n1-question-bank` repository
(default path `../jlpt-n1-question-bank`, override with `JLPT_QB_ROOT`).
Adding future words to the study material and re-running the two tools
updates the PDF automatically (漢字 "to be appeared" included).

## 出典 / Public licensing

See [CITATION.md](CITATION.md).