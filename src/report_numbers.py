"""Single source of truth for every number quoted in the paper, report and slides.

Writes results/numbers.json (used by the report and slides) and
paper/generated/{numbers.tex, tab_*.tex} (used by the LaTeX paper via \\val{key}).

Usage: python src/report_numbers.py
"""
from __future__ import annotations

import json

import pandas as pd

from config import DRAVIDIAN, INDIC, INDO_ARYAN, LANGS, RESULTS, ROOT

GEN = ROOT / "paper" / "generated"
GROUPS = {"ia": INDO_ARYAN, "dr": DRAVIDIAN, "indic": INDIC, "eng": ["eng_Latn"]}
METRICS = {"fertility": 2, "parity": 2, "asr": 1, "intra_char_split": 1, "pcw": 2, "words_in_8k": 0,
           "unk_rate": 1, "chars_per_token": 2, "renyi_efficiency": 3}


def fmt(v, nd):
    if pd.isna(v):
        return "N/A"
    return f"{v:,.{nd}f}" if nd == 0 else f"{v:.{nd}f}"


def fmt_p(p):
    if pd.isna(p):
        return "N/A"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def build() -> dict:
    s = pd.read_csv(RESULTS / "benchmark_summary.csv")
    info = pd.read_csv(RESULTS / "tokenizer_info.csv").set_index("tokenizer")
    V: dict[str, str] = {}
    raw: dict[str, float] = {}

    def put(key, value, nd=2):
        raw[key] = None if pd.isna(value) else float(value)
        V[key] = fmt(value, nd)

    for tk, g in s.groupby("tokenizer"):
        put(f"vocab:{tk}", info.loc[tk, "vocab_size"], 0)
        V[f"label:{tk}"] = info.loc[tk, "label"]
        for m, nd in METRICS.items():
            for grp, langs in GROUPS.items():
                put(f"{m}:{tk}:{grp}", g[g.lang.isin(langs)][m].mean(), nd)
            for _, r in g.iterrows():
                put(f"{m}:{tk}:{r.lang}", r[m], nd)
        for _, r in g.iterrows():
            for b in ("fertility_lo", "fertility_hi", "asr_lo", "asr_hi"):
                if b in r and not pd.isna(r[b]):
                    put(f"{b}:{tk}:{r.lang}", r[b], 2 if b.startswith("fert") else 1)

    # Wilcoxon: Sarvam-1 vs Sarvam-30B
    w = pd.read_csv(RESULTS / "wilcoxon_sarvam1_vs_30b.csv")
    for _, r in w.iterrows():
        k = f"{r.metric}:{r.lang}"
        put(f"wsv:median_a:{k}", r.median_a, 2)
        put(f"wsv:median_b:{k}", r.median_b, 2)
        V[f"wsv:p:{k}"] = fmt_p(r.p_holm)
        put(f"wsv:r:{k}", r.rank_biserial, 2)
    for metric, g in w.groupby("metric"):
        V[f"wsv:n_b_better:{metric}"] = str(int((g.median_b < g.median_a).sum()))
        V[f"wsv:n_b_worse:{metric}"] = str(int((g.median_b > g.median_a).sum()))
        V[f"wsv:n_sig:{metric}"] = str(int((g.p_holm < 0.05).sum()))
    # Wilcoxon: Indo-Aryan vs Dravidian
    f = pd.read_csv(RESULTS / "wilcoxon_ia_vs_dravidian.csv")
    for _, r in f.iterrows():
        k = f"{r.metric}:{r.tokenizer}"
        put(f"wfam:ratio:{k}", r.ratio_dr_over_ia, 2)
        put(f"wfam:ia:{k}", r.mean_indo_aryan, 2)
        put(f"wfam:dr:{k}", r.mean_dravidian, 2)
        V[f"wfam:p:{k}"] = fmt_p(r.p_holm)
        put(f"wfam:r:{k}", r.rank_biserial, 2)
    for metric, g in f.groupby("metric"):
        V[f"wfam:n_dr_higher:{metric}"] = str(int(((g.ratio_dr_over_ia > 1) & (g.p_holm < 0.05)).sum()))
        V[f"wfam:n_total:{metric}"] = str(len(g))

    # Training + akshara inventory
    tl = json.loads((RESULTS / "training_log.json").read_text(encoding="utf-8"))
    inv = tl["_akshara_inventory"]
    put("inv:types", inv["types"], 0)
    put("inv:types_ge2", inv["types_freq_ge2"], 0)
    put("inv:tokens", inv["tokens"], 0)
    for name, d in tl.items():
        if name.startswith("_"):
            continue
        put(f"train:seconds:{name}", d["train_seconds"], 1)
        if d.get("akshara_atomic"):
            put(f"train:mapped:{name}", d["mapped_types"], 0)
            put(f"train:coverage:{name}", 100 * d["token_coverage"], 2)
    cov = json.loads((RESULTS / "akshara_coverage.json").read_text(encoding="utf-8"))
    for size in ("16k", "32k", "64k"):
        a, b = cov.get(f"ours-akshara-bpe-{size}", {}), cov.get(f"ours-bpe-{size}", {})
        if "tokens" in a and "tokens" in b:
            put(f"bare:extra_share_pct:{size}", 100 * (a["bare_metaspace"] - b["bare_metaspace"]) /
                (a["tokens"] - b["tokens"]), 0)
            put(f"bare:pct:ours-akshara-bpe-{size}", 100 * a["bare_metaspace"] / a["tokens"], 1)
            put(f"bare:pct:ours-bpe-{size}", 100 * b["bare_metaspace"] / b["tokens"], 1)
    for name, d in cov.items():
        if "outside_inventory_pct" not in d:
            continue
        put(f"cov:oov_pct:{name}", d["outside_inventory_pct"], 2)
        put(f"cov:split_mapped:{name}", d["split_mapped"], 0)
        put(f"cov:split_unmapped:{name}", d["split_unmapped"], 0)
        put(f"cov:aksharas:{name}", d["aksharas"], 0)

    # Relative changes for RQ4 (64K)
    for size in ("16k", "32k", "64k"):
        a, b = f"ours-akshara-bpe-{size}", f"ours-bpe-{size}"
        if a in set(s.tokenizer) and b in set(s.tokenizer):
            fa = s[(s.tokenizer == a) & s.lang.isin(INDIC)].fertility.mean()
            fb = s[(s.tokenizer == b) & s.lang.isin(INDIC)].fertility.mean()
            put(f"rq4:fert_increase_pct:{size}", 100 * (fa / fb - 1), 1)
            ra = s[(s.tokenizer == a) & s.lang.isin(INDIC)].asr.mean()
            rb = s[(s.tokenizer == b) & s.lang.isin(INDIC)].asr.mean()
            put(f"rq4:asr_reduction_pct:{size}", 100 * (1 - ra / rb), 1)
    # Lineage
    for d in json.loads((RESULTS / "vocab_lineage.json").read_text(encoding="utf-8")):
        key = "sarvam30b_gemma3" if d["a"].startswith("Sarvam-30B") else "sarvamm_mistral"
        for fld in ("vocab_a", "vocab_b", "shared_string_and_id", "only_in_a", "only_in_b"):
            if fld in d:
                put(f"lin:{key}:{fld}", d[fld], 0)
        if "shared_string_and_id" in d:
            put(f"lin:{key}:shared_pct", 100 * d["shared_string_and_id"] / d["vocab_a"], 1)
            put(f"lin:{key}:replaced_pct", 100 * d["only_in_a"] / d["vocab_a"], 1)
        for sc, n in d.get("only_in_a_by_script", {}).items():
            put(f"lin:{key}:a_only:{sc}", n, 0)
        for sc, n in d.get("only_in_b_by_script", {}).items():
            put(f"lin:{key}:b_only:{sc}", n, 0)
    # Vocabulary share
    vs = pd.read_csv(RESULTS / "vocab_indic_share.csv")
    for _, r in vs.iterrows():
        put(f"vshare:pct:{r.tokenizer}", r.indic_pct, 1)
        put(f"vshare:n:{r.tokenizer}", r.indic_tokens, 0)
    vc = pd.read_csv(RESULTS / "vocab_composition.csv")
    for _, r in vc.iterrows():
        put(f"vcomp:n:{r.tokenizer}:{r.script}", r.n_tokens, 0)
        put(f"vcomp:pct:{r.tokenizer}:{r.script}", r.pct, 1)
    # Corpus / data
    cs = json.loads((RESULTS / "corpus_stats.json").read_text(encoding="utf-8"))
    put("data:train_per_lang", cs["per_lang_target"], 0)
    put("data:train_total", sum(x["train_sentences"] for x in cs["languages"]), 0)
    put("data:overlap_removed", sum(x["eval_overlap"] for x in cs["languages"]), 0)
    put("data:heldout_total", sum(x["heldout_sentences"] for x in cs["languages"]), 0)
    put("data:flores_per_lang", s.n_sentences.iloc[0], 0)
    sl = pd.read_csv(RESULTS / "sentence_level.csv.gz", usecols=["tokenizer", "span_mode"])
    ok = sl.assign(ok=sl.span_mode != "none").groupby("tokenizer").ok.agg(["sum", "size"])
    put("span:min_ok", ok["sum"].min(), 0)
    put("span:total", ok["size"].iloc[0], 0)
    meta = json.loads((RESULTS / "run_metadata.json").read_text(encoding="utf-8"))
    put("mirror:llama_base_tokens", meta["mirror_verification"]["llama-3.1"]["official_base_tokens"], 0)
    import sys
    sys.path.insert(0, str(ROOT / "tests"))
    from test_akshara import CASES
    put("n:akshara_cases", len(CASES), 0)
    put("n:akshara_scripts", 9, 0)
    a = s[(s.tokenizer == "ours-akshara-bpe-64k") & s.lang.isin(INDIC)].asr.mean()
    b = s[(s.tokenizer == "sarvam-1") & s.lang.isin(INDIC)].asr.mean()
    put("rq4:asr_ratio_sarvam1_over_ours64k", b / a, 0)
    put("n:tokenizers_published", len([t for t in s.tokenizer.unique() if not t.startswith("ours")]), 0)
    put("n:tokenizers_ours", len([t for t in s.tokenizer.unique() if t.startswith("ours")]), 0)
    return {"values": V, "raw": raw}


def latex_escape(s: str) -> str:
    return (s.replace("\\", r"\textbackslash{}").replace("%", r"\%").replace("&", r"\&").replace("_", r"\_")
            .replace("#", r"\#").replace("<", r"$<$").replace(">", r"$>$"))


def write_tex(V: dict):
    GEN.mkdir(parents=True, exist_ok=True)
    lines = ["% generated by src/report_numbers.py -- do not edit",
             r"\makeatletter",
             r"\newcommand{\val}[1]{\ifcsname val@#1\endcsname\csname val@#1\endcsname"
             r"\else\errmessage{undefined value key #1}\fi}"]
    for k, v in V.items():
        lines.append(r"\expandafter\def\csname val@" + k + r"\endcsname{" + latex_escape(v) + "}")
    lines.append(r"\makeatother")
    (GEN / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


ZOO_ROWS = ["sarvam-1", "sarvam-m", "sarvam-30b", "gpt-4o", "gpt-4", "llama-3.1", "gemma-3", "qwen-2.5",
            "muril", "indicbert-v2", "xlm-r", "mbert", "ours-bpe-64k", "ours-akshara-bpe-64k", "ours-unigram-64k"]


def write_tables(V: dict):
    info = pd.read_csv(RESULTS / "tokenizer_info.csv").set_index("tokenizer")
    rows = [k for k in ZOO_ROWS if k in info.index]
    # Table: tokenizer zoo
    fam = {"bytes": "bytes", "offsets": "offsets"}
    t = [r"\begin{tabular}{@{}llrl@{}}", r"\toprule", r"Tokenizer & Algorithm & Vocab & Spans \\", r"\midrule"]
    for k in rows:
        if k.startswith("ours") and not rows[rows.index(k) - 1].startswith("ours"):
            t.append(r"\midrule")
        t.append(f"{latex_escape(info.loc[k, 'label'])} & {latex_escape(info.loc[k, 'family'])} & "
                 f"{int(info.loc[k, 'vocab_size']):,} & {fam.get(info.loc[k, 'span_mode'], 'none')} \\\\")
    t += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_zoo.tex").write_text("\n".join(t) + "\n", encoding="utf-8")
    # Table: main results
    t = [r"\begin{tabular}{@{}lrrrrrrr@{}}", r"\toprule",
         r" & \multicolumn{3}{c}{Fertility} & \multicolumn{2}{c}{Parity} & \multicolumn{2}{c}{ASR (\%)} \\",
         r"\cmidrule(lr){2-4}\cmidrule(lr){5-6}\cmidrule(l){7-8}",
         r"Tokenizer & En & IA & Dr & IA & Dr & IA & Dr \\", r"\midrule"]
    for k in rows:
        if k.startswith("ours") and not rows[rows.index(k) - 1].startswith("ours"):
            t.append(r"\midrule")
        c = [V[f"fertility:{k}:eng"], V[f"fertility:{k}:ia"], V[f"fertility:{k}:dr"], V[f"parity:{k}:ia"],
             V[f"parity:{k}:dr"], V[f"asr:{k}:ia"], V[f"asr:{k}:dr"]]
        t.append(latex_escape(V[f"label:{k}"]) + " & " + " & ".join(c) + r" \\")
    t += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_main.tex").write_text("\n".join(t) + "\n", encoding="utf-8")
    # Table: our tokenizers
    t = [r"\begin{tabular}{@{}lrrrrr@{}}", r"\toprule",
         r"Model & Fert. & Parity & ASR & PCW & Mapped \\", r"\midrule"]
    for size in ("16k", "32k", "64k"):
        for k in (f"ours-bpe-{size}", f"ours-akshara-bpe-{size}"):
            if f"label:{k}" not in V:
                continue
            mapped = V.get(f"train:mapped:{k}", "--")
            t.append(f"{latex_escape(V[f'label:{k}'].replace('Ours ', ''))} & {V[f'fertility:{k}:indic']} & "
                     f"{V[f'parity:{k}:indic']} & {V[f'asr:{k}:indic']} & {V[f'pcw:{k}:indic']} & {mapped} \\\\")
    if "label:ours-unigram-64k" in V:
        k = "ours-unigram-64k"
        t.append(f"Unigram 64K & {V[f'fertility:{k}:indic']} & {V[f'parity:{k}:indic']} & {V[f'asr:{k}:indic']} & "
                 f"{V[f'pcw:{k}:indic']} & -- \\\\")
    t.append(r"\midrule")
    for k in ("sarvam-1", "sarvam-30b"):
        t.append(f"{latex_escape(V[f'label:{k}'])} & {V[f'fertility:{k}:indic']} & {V[f'parity:{k}:indic']} & "
                 f"{V[f'asr:{k}:indic']} & {V[f'pcw:{k}:indic']} & -- \\\\")
    t += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_ours.tex").write_text("\n".join(t) + "\n", encoding="utf-8")
    # Table: Sarvam-1 vs Sarvam-30B per language
    t = [r"\begin{tabular}{@{}lrrrr@{}}", r"\toprule",
         r"Language & S-1 & S-30B & $p_{\mathrm{Holm}}$ & $r$ \\", r"\midrule"]
    for lang in INDIC:
        k = f"fertility:{lang}"
        t.append(f"{LANGS[lang]['name']} & {V[f'fertility:sarvam-1:{lang}']} & {V[f'fertility:sarvam-30b:{lang}']} & "
                 f"{latex_escape(V[f'wsv:p:{k}'])} & {V[f'wsv:r:{k}']} \\\\")
    t += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_sarvam.tex").write_text("\n".join(t) + "\n", encoding="utf-8")


def main():
    out = build()
    (RESULTS / "numbers.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    write_tex(out["values"])
    write_tables(out["values"])
    print(f"{len(out['values'])} values written")


if __name__ == "__main__":
    main()
