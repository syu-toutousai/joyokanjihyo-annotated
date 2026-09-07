# 常用漢字表 — JLPT N1 学習リンク版

An an `常用漢字表`（平成22年内閣告示第2号）student edition. Every 漢字 that
appears in our JLPT N1 2024 vocabulary study material is marked with a small
**icon cluster** placed in the whitespace band directly **above** the kanji
entry (so it never touches the kanji or the 音・訓・例 columns after it), and
the glyph is **hyperlinked** to the corresponding word card on the 学習材料
page of the
[`jlpt-n1-question-bank`](https://github.com/syu-toutousai/jlpt-n1-question-bank)
repository.

Each icon is a colour-coded shape (一目で了解):

| icon | meaning |
| ---- | ------- |
| `20/24` navy rectangle | 2024 年度 |
| red circle with `N1` | JLPT N1 |
| `①` indigo circle | 問題1 (語彙・文法 reading) |
| `②` orange circle | 問題2 (語彙・文法 context) |

A kanji in both blocks carries both `①` and `②`.

Clicking the kanji (or its icon cluster) jumps to the word card in the
学習材料 page:

`vocab-words.html#w-<word>`

## Files

| file | description |
| ---- | ----------- |
| `src/joyokanjihyo_20101130.pdf` | original official PDF (unchanged) |
| `src/joyokanjihyo_20101130_annotated.pdf` | our annotated edition (badges + links) |
| `tools/kanji_map.py` | extracts 漢字 → 問/link map from the study material |
| `tools/annotate_pdf.py` | draws badges + link annotations onto the PDF |
| `data/kanji_labels.json` | kanji → {問, Q, words, url} generated map |
| `data/questions.json` | hand-inputted exam questions, validated & cited |
| `data/prev_*.png` | preview renders (git-ignored, for inspection) |

## 注釈の種類（annotated PDF に含まれる 3 種）

1. **アイコンバッジ** – 教材由来の常用漢字（本表エントリ）の字形直上余白帯に
   アイコン群（2024 / N1 / ①・②）を描き、語彙カード（`#w-…`）or 問題（`#q…`）
   へのリンクを付す。
2. **語のハイライト（黄色）** – 教材の語（漢字単語）が本表の音・訓・例・備考欄に
   現れている場合、その語をへば標し語彙カードへリンク（`tools/annotate_pdf.py`
   `highlight_words`）。
3. **付録（表外漢字）** – 常用漢字表に収録されない文字（表外）を、末尾の新ページに
   本表と同じ体裁（字形・音・訓・例・備考＋アイコン・リンク）で追記。

### Hand-inputted questions (語幹漢字 ネット追加)

手入力した問題は `data/questions.json` に記録します（語幹・選択肢・正解・
検証ソース一式）。`tools/kanji_map.py` は語幹・選択肢の漢字も取り込みます:

- カード語由来の漢字は従来どおり語彙カード（`#w-…`）へリンク
- 語幹にしか現れない漢字（例: 遺・跡・覆）は当該問題（`#q7` など）へリンク

例: `2024-07 N1 語彙 問題2(7) 遺跡の発見…説を覆す` — 当初の手入力「処点」
は誤りで「拠点」が正しいことを 5 件の公開ソース（採点表・復元サイト）で
検証済み（`questions.json` の `sources`）。

## Why two features are skipped for some kanji

- 咎・脆 come from 2024 N1 words but are **outside** the `常用漢字表`
  (表外漢字), so they have no 本表 entry to badge. They are instead
  appended on a new 付録 page (same layout as 本表: 字形・音・訓・例・備考
  ＋ アイコン＋リンク). USER: 表外由此追加。

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