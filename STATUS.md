# STATUS

## Placeholders
Filled: Reg. No. `23FE10CII00213`, course "Natural Language Processing (NLP)", guide "Heena Kalim"
(report cover, certificate, declaration, acknowledgement; slide 1).

The guide's designation line was removed from the certificate (edited in Word; `scripts/build_report.py` matches).

Still to fill by hand: signatures and dates on the certificate and declaration pages (blank lines, meant for the
printed copy).

## Done
- **Phase 0**: venv (Python 3.11), requirements, repo layout, git; `gh` already authenticated as `jkknikhil-git`.
  Project lives on D: (`D:\PROJECTS\indic-tokenizer-study`) because C: has little free space; Hugging Face cache is
  inside the project (`.cache/`).
- **Phase 1**: FLORES-200 devtest from the official tarball (1,012 sentences x 12 languages). Training corpus: 50,000
  train + 100 held-out sentences per language streamed from `ai4bharat/sangraha` (verified split, shards
  data-0/data-1). 0 sentences overlapped FLORES dev+devtest. See `results/corpus_stats.json`.
- **Phase 2**: 13 tokenizers loaded, all ungated. Sarvam-30B and 105B have identical vocab+merges (sha256) and are
  reported as one row. Mirrors verified: Llama-3.1 (unsloth) matches Meta's official `llama-models` tokenizer file
  token-for-token; Gemma-3 (unsloth) has identical git blob hashes to `google/gemma-3-1b-it`. Byte-span adapters
  validated on >= 12,119 / 12,144 sentences per tokenizer.
- **Phase 3**: metrics (fertility, chars/bytes per token, parity, PCW, ASR, intra-char splits, words per 8K, UNK
  rate, Renyi efficiency), bootstrap CIs (1,000 resamples), paired Wilcoxon tests with Holm correction, vocabulary
  composition and vocabulary lineage (Sarvam-30B vs Gemma-3, Sarvam-M vs Mistral-Small-3.1).
- **Phase 4**: standard BPE and akshara-atomic BPE at 16K/32K/64K + Unigram 64K. All trained in < 4 minutes each.
  Round-trip test passes on 1,000 held-out sentences for all 7 models.
- **Phase 5**: 9 figures (PNG 300 dpi + PDF), each inspected; Indic text renders correctly (matplotlib 3.11 shapes
  complex scripts).
- **Phase 6**: 6-page IEEE paper `paper/main.pdf` (tectonic/XeLaTeX), `paper/overleaf.zip` (compile with XeLaTeX).
  All numbers come from `paper/generated/numbers.tex` (written by `src/report_numbers.py`); no overfull boxes or
  undefined references. Every reference was checked against arXiv, the ACL Anthology, NeurIPS proceedings,
  OpenReview, or the official blog/repository (ACL BibTeX taken verbatim from the Anthology).
- **Phase 7**: university report `report/report.docx` + `report/report.pdf` (27 pages; chapters 1-6 are 15 pages), generated with python-docx and converted to PDF with Microsoft Word.
- **Phase 8**: 14-slide deck with speaker notes, exported to PDF with PowerPoint and checked visually.
- **Phase 9**: README, tests (77 passing), public GitHub repo https://github.com/jkknikhil-git/indic-tokenizer-study (created and pushed by you; verified).

## Skipped / failed / deviations
- `ai4bharat/IN22-Gen` is gated (`gated=auto`, needs a login), so it was skipped; FLORES-200 is the only benchmark.
- LibreOffice was not installed (the download mirror ran at about 15 KB/s); Microsoft Word/PowerPoint were used for
  rendering instead.
- Sarvam-30B/105B release date: the official blog is dated **6 March 2026** (the brief said Feb 2026); the paper
  uses the blog date.
- Akshara-atomic BPE maps at most V/2 aksharas, because the 22,221 akshara types with frequency >= 2 do not fit in a
  16K vocabulary. Documented in the paper as a design parameter.
- mBERT maps 85.8% of Odia tokens to `[UNK]`; its Odia fertility is flagged as an artefact in the heatmap and paper.
- Sarvam-M loads with a transformers warning about Mistral's pre-tokenizer regex; we measured the tokenizer exactly
  as shipped.
- Compute: total well under the 2-hour budget (corpus about 2 min, all training about 10 min, metrics about 2 min).

## Next (optional)
- Fill the guide's designation and the signatures/dates in `report/report.docx`.
- Future work listed in the paper: downstream LM training, IN22, word-initial akshara variants.

## Final check (scripts/final_check.py)
- 5 random paper numbers recomputed independently from `results/sentence_level.csv.gz`: all match.
- 96 distinct values quoted in the paper, all defined; all 9 referenced figures exist and are newer than the results.
