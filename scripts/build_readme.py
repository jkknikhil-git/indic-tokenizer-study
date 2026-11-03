"""Write README.md with the key-results table filled from results/numbers.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V = json.loads((ROOT / "results" / "numbers.json").read_text(encoding="utf-8"))["values"]
REPO = "https://github.com/jkknikhil-git/indic-tokenizer-study"
ROWS = ["sarvam-1", "sarvam-m", "sarvam-30b", "gpt-4o", "gpt-4", "llama-3.1", "gemma-3", "qwen-2.5", "muril",
        "indicbert-v2", "xlm-r", "mbert", "ours-bpe-64k", "ours-akshara-bpe-64k", "ours-unigram-64k"]


def v(k):
    return V[k]


def table():
    head = ("| Tokenizer | Vocab | Fertility IA | Fertility Dr | Parity IA | Parity Dr | ASR IA (%) | ASR Dr (%) |\n"
            "|---|---:|---:|---:|---:|---:|---:|---:|")
    rows = []
    for k in ROWS:
        if f"label:{k}" not in V:
            continue
        name = f"**{V[f'label:{k}']}**" if k.startswith("ours-akshara") else V[f"label:{k}"]
        rows.append(f"| {name} | {v(f'vocab:{k}')} | {v(f'fertility:{k}:ia')} | {v(f'fertility:{k}:dr')} | "
                    f"{v(f'parity:{k}:ia')} | {v(f'parity:{k}:dr')} | {v(f'asr:{k}:ia')} | {v(f'asr:{k}:dr')} |")
    return head + "\n" + "\n".join(rows)


README = f"""# Measuring the Indic Tokenizer Tax

**A comparative study of Sarvam AI's tokenizers and akshara-aware subword segmentation for Indian languages**
(NLP course project, Nikhileshwar Jakka, Manipal University Jaipur)

The same sentence costs very different numbers of tokens in different languages. This project measures that
"tokenizer tax" for 11 Indian languages on the parallel FLORES-200 devtest set across
{v('n:tokenizers_published')} published tokenizers, with a focus on Sarvam AI's three model generations. It recovers
exact UTF-8 byte spans for every token, which makes it possible to measure how often tokenizers break
**aksharas** (the orthographic syllables of Brahmic scripts). It also introduces **akshara-atomic BPE**, which gives
every frequent akshara its own base symbol so that BPE can never split it. Main findings:

- **Sarvam-M** reuses the Mistral-Small-3.1 vocabulary unchanged ({v('lin:sarvamm_mistral:shared_string_and_id')}
  identical entries). **Sarvam-30B/105B** shares {v('lin:sarvam30b_gemma3:shared_pct')}% of its vocabulary, with
  identical ids, with **Gemma-3**; {v('lin:sarvam30b_gemma3:only_in_a')} slots were re-assigned to Indic scripts.
- Compared with Sarvam-1, Sarvam-30B is cheaper on {v('wsv:n_b_better:fertility')} languages but more expensive on
  {v('wsv:n_b_worse:fertility')}, **including all four Dravidian languages**. The Dravidian/Indo-Aryan fertility
  ratio grows from {v('wfam:ratio:fertility:sarvam-1')} to {v('wfam:ratio:fertility:sarvam-30b')}.
- Byte-level tokenizers break almost every akshara (Llama-3.1: {v('asr:llama-3.1:indic')}%). At 64K,
  **akshara-atomic BPE** cuts the Akshara Split Rate from {v('asr:ours-bpe-64k:indic')}% to
  {v('asr:ours-akshara-bpe-64k:indic')}% for a {v('rq4:fert_increase_pct:64k')}% fertility cost.

## Key results (FLORES-200 devtest; IA = Indo-Aryan, Dr = Dravidian; means over languages)

{table()}

Fertility = tokens per whitespace word. Parity = tokens relative to the parallel English sentences (the API cost
multiplier). ASR = Akshara Split Rate, the % of aksharas that contain a token boundary. Full per-language results with
95% bootstrap CIs: [`results/benchmark_summary.csv`](results/benchmark_summary.csv).

| Fertility | Akshara splits | Akshara-atomic BPE |
|---|---|---|
| ![](figures/fig1_fertility_heatmap.png) | ![](figures/fig4_asr.png) | ![](figures/fig6_ours_vs_vocab.png) |

![Token visualisation](figures/fig7_token_visualisation.png)

## Reproduce

Everything runs on a CPU laptop (about 15 minutes, plus downloads). Only tokenizer files are downloaded, never model
weights, and no Hugging Face login is needed.

```bash
bash scripts/run_all.sh          # Git Bash / Linux / macOS
```
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_all.ps1   # Windows PowerShell
```

This downloads FLORES-200 and fonts, streams the Sangraha training corpus, trains our tokenizers, computes every
metric and statistic, and redraws all figures. Afterwards:

- `python src/report_numbers.py` regenerates every number used by the paper, report and slides
- `python scripts/build_paper.py` builds `paper/main.pdf` (needs [tectonic](https://tectonic-typesetting.github.io)) and `paper/overleaf.zip`
- `python scripts/build_report.py` and `python scripts/build_slides.py` rebuild the report and slides
- `pytest` runs the akshara, metric and round-trip tests

`python scripts/show_results.py [summary|lineage|sarvam|family|ours]` prints the headline results, and
`python scripts/make_screenshots.py` saves the real output of the tests, the consistency check and those
result tables as images in [`screenshots/`](screenshots/).

Library versions, seeds, dataset sources, sentence counts and tokenizer revisions are logged in
[`results/run_metadata.json`](results/run_metadata.json).

## Repository map

```
src/
  config.py            languages, paths, seeds
  data.py              FLORES loader; Sangraha streaming, dedup, eval-overlap removal
  tokenizers_zoo.py    common interface + byte-span adapters (tiktoken, byte-level BPE, SentencePiece, WordPiece)
  akshara.py           akshara segmenter (grapheme clusters + virama joining, per-script rules)
  metrics.py           fertility, parity, ASR, PCW, intra-char splits, effective context, Renyi efficiency
  stats.py             bootstrap CIs, paired Wilcoxon tests, Holm correction
  vocab_analysis.py    vocabulary script composition + Sarvam lineage comparison
  train_tokenizers.py  standard BPE, akshara-atomic BPE, Unigram (SentencePiece)
  plots.py             figures (300 dpi PNG + PDF)
  report_numbers.py    single source of truth for every quoted number
  metadata.py          run_metadata.json + mirror verification
scripts/               run_all.sh / run_all.ps1, paper/report/slides builders
tests/                 pytest: akshara segmentation, metrics, round-trip
models/                our trained tokenizers (+ akshara mapping tables)
results/               CSV + JSON results
figures/               all figures
paper/                 IEEE paper (main.tex, main.pdf, overleaf.zip)
report/                university project report (.docx, .pdf)
slides/                presentation (.pptx, .pdf)
```

## Notes and limitations

- `ai4bharat/IN22-Gen` is gated on the Hugging Face Hub, so FLORES-200 is the only benchmark.
- Llama-3.1 and Gemma-3 tokenizers come from public mirrors (`unsloth/*`). The Llama-3.1 vocabulary matches Meta's
  official `llama-models` tokenizer file token-for-token, and the Gemma-3 files have the same git blob hashes as
  Google's repository (see `results/run_metadata.json`).
- mBERT maps {v('unk_rate:mbert:ory_Orya')}% of Odia tokens to `[UNK]`, so its low Odia fertility is an artefact.
- All metrics are intrinsic; no language models were trained.

## Citation

```bibtex
@misc{{jakka2026indictokenizertax,
  title  = {{Measuring the Indic Tokenizer Tax: A Comparative Study of Sarvam AI's Tokenizers and
            Akshara-Aware Subword Segmentation for Indian Languages}},
  author = {{Jakka, Nikhileshwar}},
  year   = {{2026}},
  howpublished = {{\\url{{{REPO}}}}}
}}
```

## Licence

Code: MIT (see [LICENSE](LICENSE)). FLORES-200 is CC BY-SA 4.0; Sangraha and the third-party tokenizers keep their
own licences. Noto fonts (downloaded, not committed) are under the SIL Open Font License.
"""

(ROOT / "README.md").write_text(README, encoding="utf-8")
print("wrote README.md")
