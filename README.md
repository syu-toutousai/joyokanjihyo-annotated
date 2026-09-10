# 常用漢字表 — JLPT N1 学習リンク版

An annotated `常用漢字表`（平成22年内閣告示第2号）student edition. Every 漢字
that appears anywhere in the JLPT N1 question bank – **2010-07 … 2025-07 の全 27 場**，
all sections 語彙・文法・読解・聴解（聴解は原文テキストのカナ行のみ） – is
marked with a small **icon cluster** placed in the whitespace band directly
**above** the kanji entry (so it never touches the kanji or the 音・訓・例
columns after it), and the entry is **hyperlinked** to the corresponding
material of the
[`jlpt-n1-question-bank`](https://github.com/syu-toutousai/jlpt-n1-question-bank)
repository.

Each icon is a colour-coded shape (一目で了解):

| icon | meaning |
| ---- | ------- |
| `10-25` navy rectangle | 収録年度の範囲（単年は `24`。全 27 場にまたがる） |
| red circle with `N1` | JLPT N1 |
| `語` orange circle | 語彙 section |
| `文` green circle | 文法 section |
| `読` blue circle | 読解 section |
| `聴` red circle | 聴解 section（原文テキスト） |

A kanji in several sections carries one circle per section; the circle colours
match the section colours of the question-bank site.

Clicking the kanji (or its icon cluster) jumps to the most specific public
target, in this order:

1. a 語彙カード word  → `vocab-words*.html#w-<word>`（公開・フラッグシップ 2024-07
   以外の 26 場は `vocab-words-<session>.html`）
2. a 語彙 問題1/2 stem → `vocab-words*.html#q<1..13>`（公開・2024-07/12 のみ
   用意）
3. anything else (文法 / 読解 / 聴解 / 過去の 問題1・2) → deep link into the
   encrypted bank: `index.html#q=<question-id>`（opens the 日题库 app on that
   exact question）

## Files

| file | description |
| ---- | ----------- |
| `src/joyokanjihyo_20101130.pdf` | original official PDF (unchanged) |
| `src/joyokanjihyo_20101130_annotated.pdf` | our annotated edition (badges + links) |
| `tools/kanji_map.py` | builds the 漢字 → 問/link map from the whole question bank |
| `tools/annotate_pdf.py` | draws badges + link annotations onto the PDF |
| `data/kanji_labels.json` | kanji → {papers, sections, q, words, url} generated map |
| `data/questions.json` | hand-inputted 2024-07 問題2 questions, validated & cited |
| `data/prev_*.png` | preview renders (git-ignored, for inspection) |

## 注釈の種類（annotated PDF に含まれる 3 種）

1. **アイコンバッジ** – 問題バンク由来の漢字（本表 1764 字）の字形直上余白帯に
   アイコン群（年度範囲 / N1 / 語・文・読・聴、右寄せ）を描き、上記リンク先
   （`#w-…` / `#q…` / `index.html#q=…`）へのリンクを付す。
2. **語のハイライト（黄色）** – 教材の語（漢字単語）が本表の音・訓・例・備考欄に
   現れている場合、その語をマーカー色で標し語彙カードへリンク
   （`tools/annotate_pdf.py` `highlight_words`、2024-12 頁のカード ID は `★` 付き
   なので実ページのアンカー (`data-w`) を読んで正しく張る）。
3. **付録（表外漢字）** – 常用漢字表に収録されない文字（表外）を、末尾の新ページに
   本表と同じ体裁（字形・音・訓・例・備考＋アイコン・リンク）で追記。

## リンク先の優先順位とデータ源

`tools/kanji_map.py` は `past-exams/**/*.json`（全 27 場、計 2,746 問）を走査します:

- 語幹・選択肢・正解の漢字（語彙・文法・読解）
- 聴解は `explanation` の **カナ行のみ**（カナ密度 ≧ 40% の行）を原文として
  採集。中国語翻訳文（日本語語名を埋め込むことがある）は判定から除外。
- 出題ソースに混入する簡体字・字体化け（処理→处里 など）は、正規日本語の
  読みを持たない／化け専用の字形として Unihan（`refs/unihan`）で除去し、
  LABELS・検索・付録のいずれにも含めない。

カード語（見出し語＋干扰项）は全 27 場の学習材料ページ
（`vocab-words.html`・`vocab-words-<session>.html`）から、実ページの
`data-w` アンカーを読んで収集。

結果: 1,966 字 = 本表 1,764 + 表外付録 202。リンク 1,043 件が公開ページ、
923 件が暗号サイトへの deep-link。

## Why some kanji are in the 付録 instead of the 本表

常用漢字表に収録されない表外字（迂・闊・饗・馴・辿・詫・這・汲 ほか 202 字、
本表と同じ体裁: 字形・音・訓・例・備考 ＋ アイコン＋リンク）。音・訓は Unihan 8.0
の kJapaneseOn / kun による既存 `EXTRA` 分のみ付与、例は問題バンクでの実例。
（括弧内の異体字 龍・亞・廣・晝・澤 などは「本表の字形欄」として捕捉し、付録には
入れない。）

## Rebuilding

```sh
python3 -m venv .venv && .venv/bin/pip install pymupdf
.venv/bin/python tools/kanji_map.py      # needs the sibling repo checked out
.venv/bin/python tools/annotate_pdf.py
```

`tools/kanji_map.py` reads the sibling `jlpt-n1-question-bank` repository
(override with `JLPT_QB_ROOT=/path/to/jlpt-n1-question-bank`; without it the
default is `parents[2]/jlpt-n1-question-bank`, which is normally wrong).
Adding future questions or words to the material and re-running the two tools
updates the PDF automatically.

## 出典 / Public licensing

See [CITATION.md](CITATION.md).