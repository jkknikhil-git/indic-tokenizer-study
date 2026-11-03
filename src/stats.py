"""Bootstrap confidence intervals and paired Wilcoxon signed-rank tests.

Usage: python src/stats.py
Reads results/sentence_level.csv.gz; writes results/bootstrap_ci.csv,
results/wilcoxon_sarvam1_vs_30b.csv, results/wilcoxon_ia_vs_dravidian.csv and adds
CI columns to results/benchmark_summary.csv.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from config import DRAVIDIAN, INDIC, INDO_ARYAN, LANGS, RESULTS, SEED

N_BOOT = 1000


def holm(pvals: np.ndarray) -> np.ndarray:
    order = np.argsort(pvals)
    m = len(pvals)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvals[i])
        adj[i] = min(1.0, running)
    return adj


def rank_biserial(x: np.ndarray, y: np.ndarray) -> float:
    """Matched-pairs rank-biserial correlation (positive => x > y)."""
    d = x - y
    d = d[d != 0]
    if len(d) == 0:
        return 0.0
    ranks = pd.Series(np.abs(d)).rank().to_numpy()
    return float((ranks[d > 0].sum() - ranks[d < 0].sum()) / ranks.sum())


def bootstrap(df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    n = df.sid.nunique()
    idx = rng.integers(0, n, size=(N_BOOT, n))  # same resamples for every tokenizer/language
    rows = []
    for (tk, lang), g in df.groupby(["tokenizer", "lang"], sort=False):
        g = g.sort_values("sid")
        tok, wrd = g.n_tokens.to_numpy(float), g.n_words.to_numpy(float)
        fert = tok[idx].sum(1) / wrd[idx].sum(1)
        row = dict(tokenizer=tk, lang=lang,
                   fertility_lo=np.percentile(fert, 2.5), fertility_hi=np.percentile(fert, 97.5))
        if lang in INDIC and g.n_aksharas.notna().any():
            # sentences without validated spans contribute nothing to either sum
            sp = g.n_split_aksharas.fillna(0).to_numpy(float)
            ak = g.n_aksharas.fillna(0).to_numpy(float)
            asr = 100 * sp[idx].sum(1) / ak[idx].sum(1)
            row.update(asr_lo=np.percentile(asr, 2.5), asr_hi=np.percentile(asr, 97.5))
        rows.append(row)
    return pd.DataFrame(rows)


def _per_sentence(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["fertility"] = d.n_tokens / d.n_words
    d["asr"] = 100 * d.n_split_aksharas / d.n_aksharas
    eng = d[d.lang == "eng_Latn"][["tokenizer", "sid", "n_tokens"]].rename(columns={"n_tokens": "eng_tokens"})
    d = d.merge(eng, on=["tokenizer", "sid"])
    d["parity"] = d.n_tokens / d.eng_tokens
    return d


def sarvam_tests(d: pd.DataFrame, a="sarvam-1", b="sarvam-30b") -> pd.DataFrame:
    rows = []
    for metric in ("fertility", "parity", "asr"):
        for lang in INDIC:
            x = d[(d.tokenizer == a) & (d.lang == lang)].set_index("sid")[metric]
            y = d[(d.tokenizer == b) & (d.lang == lang)].set_index("sid")[metric]
            j = pd.concat([x, y], axis=1, keys=["a", "b"]).dropna()
            if len(j) < 10 or (j.a == j.b).all():
                rows.append(dict(metric=metric, lang=lang, n=len(j), statistic=np.nan, p=np.nan))
                continue
            res = wilcoxon(j.a, j.b, zero_method="wilcox")
            rows.append(dict(metric=metric, lang=lang, language=LANGS[lang]["name"], n=len(j),
                             median_a=j.a.median(), median_b=j.b.median(),
                             median_diff=(j.a - j.b).median(), statistic=res.statistic, p=res.pvalue,
                             rank_biserial=rank_biserial(j.a.to_numpy(), j.b.to_numpy())))
    out = pd.DataFrame(rows)
    out["p_holm"] = np.nan
    for metric, g in out.groupby("metric"):
        ok = g.p.notna()
        out.loc[g.index[ok], "p_holm"] = holm(g.p[ok].to_numpy())
    out.insert(0, "a", a)
    out.insert(1, "b", b)
    return out


def family_tests(d: pd.DataFrame) -> pd.DataFrame:
    """Per tokenizer: mean over Indo-Aryan vs mean over Dravidian languages, paired by FLORES sentence."""
    rows = []
    for tk, g in d.groupby("tokenizer"):
        for metric in ("fertility", "parity", "asr"):
            w = g.pivot_table(index="sid", columns="lang", values=metric)
            if not set(INDO_ARYAN + DRAVIDIAN) <= set(w.columns):
                continue
            ia, dr = w[INDO_ARYAN].mean(axis=1), w[DRAVIDIAN].mean(axis=1)
            j = pd.concat([ia, dr], axis=1, keys=["ia", "dr"]).dropna()
            if len(j) < 10 or (j.ia == j.dr).all():
                continue
            res = wilcoxon(j.dr, j.ia)
            rows.append(dict(tokenizer=tk, metric=metric, n=len(j), mean_indo_aryan=j.ia.mean(),
                             mean_dravidian=j.dr.mean(), ratio_dr_over_ia=j.dr.mean() / j.ia.mean(),
                             statistic=res.statistic, p=res.pvalue,
                             rank_biserial=rank_biserial(j.dr.to_numpy(), j.ia.to_numpy())))
    out = pd.DataFrame(rows)
    out["p_holm"] = np.nan
    for metric, g in out.groupby("metric"):
        out.loc[g.index, "p_holm"] = holm(g.p.to_numpy())
    return out


def main():
    df = pd.read_csv(RESULTS / "sentence_level.csv.gz")
    ci = bootstrap(df)
    ci.to_csv(RESULTS / "bootstrap_ci.csv", index=False)
    summ = pd.read_csv(RESULTS / "benchmark_summary.csv")
    summ = summ.drop(columns=[c for c in summ.columns if c.endswith(("_lo", "_hi"))])
    summ = summ.merge(ci, on=["tokenizer", "lang"], how="left")
    summ.to_csv(RESULTS / "benchmark_summary.csv", index=False)
    d = _per_sentence(df)
    sarvam_tests(d).to_csv(RESULTS / "wilcoxon_sarvam1_vs_30b.csv", index=False)
    family_tests(d).to_csv(RESULTS / "wilcoxon_ia_vs_dravidian.csv", index=False)
    print("stats written")


if __name__ == "__main__":
    main()
