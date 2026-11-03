"""Print the headline results to the terminal.

Usage: python scripts/show_results.py [summary|lineage|sarvam|family|ours]
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))
from config import DRAVIDIAN, INDIC, INDO_ARYAN, LANGS  # noqa: E402

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)
ORDER = ["sarvam-1", "sarvam-m", "sarvam-30b", "gpt-4o", "gpt-4", "llama-3.1", "gemma-3", "qwen-2.5", "muril",
         "indicbert-v2", "xlm-r", "mbert", "ours-bpe-64k", "ours-akshara-bpe-64k", "ours-unigram-64k"]


def summary():
    s = pd.read_csv(RES / "benchmark_summary.csv")
    rows = []
    for k in ORDER:
        g = s[s.tokenizer == k]
        if g.empty:
            continue
        ia, dr = g[g.lang.isin(INDO_ARYAN)], g[g.lang.isin(DRAVIDIAN)]
        rows.append(dict(tokenizer=g.label.iloc[0], fert_IA=ia.fertility.mean(), fert_Dr=dr.fertility.mean(),
                         parity_IA=ia.parity.mean(), parity_Dr=dr.parity.mean(),
                         ASR_IA=ia.asr.mean(), ASR_Dr=dr.asr.mean()))
    print("Key results on FLORES-200 devtest (mean over Indo-Aryan / Dravidian languages)\n")
    print(pd.DataFrame(rows).round(2).to_string(index=False))


def lineage():
    for d in json.loads((RES / "vocab_lineage.json").read_text(encoding="utf-8")):
        print(f"{d['a']}  vs  {d['b']}")
        print(f"  vocabulary sizes      : {d['vocab_a']:,} vs {d['vocab_b']:,}")
        print(f"  same string and id    : {d['shared_string_and_id']:,} "
              f"({100 * d['shared_string_and_id'] / d['vocab_a']:.1f}%)")
        print(f"  only in {d['a']:<14}: {d['only_in_a']:,}  {dict(list(d['only_in_a_by_script'].items())[:6])}")
        print(f"  only in {d['b']:<14}: {d['only_in_b']:,}  {dict(list(d['only_in_b_by_script'].items())[:6])}\n")


def sarvam():
    w = pd.read_csv(RES / "wilcoxon_sarvam1_vs_30b.csv")
    w = w[w.metric == "fertility"].copy()
    w["language"] = w.lang.map(lambda l: LANGS[l]["name"])
    w["p_holm"] = w.p_holm.map(lambda p: "<0.001" if p < 0.001 else f"{p:.3f}")
    print("Sarvam-1 vs Sarvam-30B: fertility, paired Wilcoxon over 1,012 FLORES sentences (Holm-corrected)\n")
    print(w[["language", "median_a", "median_b", "p_holm", "rank_biserial"]]
          .rename(columns={"median_a": "Sarvam-1", "median_b": "Sarvam-30B", "rank_biserial": "r"})
          .round(2).to_string(index=False))


def family():
    f = pd.read_csv(RES / "wilcoxon_ia_vs_dravidian.csv")
    f = f[f.metric == "fertility"].copy()
    f["p_holm"] = f.p_holm.map(lambda p: "<0.001" if p < 0.001 else f"{p:.3f}")
    print("Indo-Aryan vs Dravidian fertility per tokenizer (paired Wilcoxon, Holm-corrected)\n")
    print(f[["tokenizer", "mean_indo_aryan", "mean_dravidian", "ratio_dr_over_ia", "p_holm"]]
          .round(2).to_string(index=False))


def ours():
    tl = json.loads((RES / "training_log.json").read_text(encoding="utf-8"))
    cov = json.loads((RES / "akshara_coverage.json").read_text(encoding="utf-8"))
    s = pd.read_csv(RES / "benchmark_summary.csv")
    print(f"Akshara inventory: {tl['_akshara_inventory']['types_freq_ge2']:,} types with frequency >= 2\n")
    rows = []
    for name, d in tl.items():
        if name.startswith("_"):
            continue
        g = s[(s.tokenizer == name) & s.lang.isin(INDIC)]
        rows.append(dict(model=name, vocab=d["vocab_size"], train_s=d["train_seconds"],
                         mapped=d.get("mapped_types", "-"), fertility=round(g.fertility.mean(), 3),
                         ASR_pct=round(g.asr.mean(), 2),
                         mapped_split=cov.get(name, {}).get("split_mapped", "-")))
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    {"summary": summary, "lineage": lineage, "sarvam": sarvam, "family": family, "ours": ours}[
        sys.argv[1] if len(sys.argv) > 1 else "summary"]()
