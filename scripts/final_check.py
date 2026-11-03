"""Final consistency checks.

1. Pick 5 random numbers quoted in the paper (\\val{...} keys) and recompute them independently from the
   sentence-level CSV (not from benchmark_summary.csv / numbers.json).
2. Confirm every figure referenced by the paper, report and slides exists and is newer than the results.
"""
import random
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from config import DRAVIDIAN, INDIC, INDO_ARYAN  # noqa: E402

GROUPS = {"ia": INDO_ARYAN, "dr": DRAVIDIAN, "indic": INDIC, "eng": ["eng_Latn"]}
NDIG = {"fertility": 2, "parity": 2, "asr": 1, "intra_char_split": 1, "pcw": 2}


def recompute(sl: pd.DataFrame, metric: str, tk: str, scope: str) -> float:
    langs = GROUPS.get(scope, [scope])
    d = sl[sl.tokenizer == tk]
    eng = d[d.lang == "eng_Latn"].set_index("sid").n_tokens
    vals = []
    for lang in langs:
        g = d[d.lang == lang]
        ok = g.dropna(subset=["n_aksharas"])
        if metric == "fertility":
            vals.append(g.n_tokens.sum() / g.n_words.sum())
        elif metric == "parity":
            vals.append(g.n_tokens.sum() / eng.loc[g.sid].sum())
        elif metric == "asr":
            vals.append(100 * ok.n_split_aksharas.sum() / ok.n_aksharas.sum())
        elif metric == "intra_char_split":
            vals.append(100 * ok.n_split_codepoints.sum() / ok.n_codepoints.sum())
        elif metric == "pcw":
            vals.append(ok.n_continued.sum() / ok.n_words_spanned.sum())
    return sum(vals) / len(vals)


def check_numbers(n=5, seed=2026):
    tex = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
    keys = sorted(set(re.findall(r"\\val\{([^}]+)\}", tex)))
    V = {}
    for line in (ROOT / "paper" / "generated" / "numbers.tex").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\\expandafter\\def\\csname val@(.+?)\\endcsname\{(.*)\}$", line)
        if m:
            V[m.group(1)] = m.group(2)
    eligible = [k for k in keys if k.split(":")[0] in NDIG and len(k.split(":")) == 3]
    sl = pd.read_csv(ROOT / "results" / "sentence_level.csv.gz")
    ok_all = True
    for k in random.Random(seed).sample(eligible, n):
        metric, tk, scope = k.split(":")
        val = recompute(sl, metric, tk, scope)
        mine = f"{val:.{NDIG[metric]}f}"
        ok = mine == V[k]
        ok_all &= ok
        print(f"{'OK ' if ok else 'BAD'} {k:45s} paper={V[k]:>8s} recomputed={mine:>8s}")
    print(f"{len(keys)} distinct values quoted in the paper; all defined: {all(k in V for k in keys)}")
    return ok_all and all(k in V for k in keys)


def check_figures():
    newest_result = (ROOT / "results" / "benchmark_summary.csv").stat().st_mtime
    refs = set()
    refs |= {Path(m).stem for m in re.findall(r"\\includegraphics\[[^]]*\]\{([^}]+)\}",
                                             (ROOT / "paper" / "main.tex").read_text(encoding="utf-8"))}
    for f in ("build_report.py", "build_slides.py"):
        refs |= set(re.findall(r'"(fig\d_[a-z_]+)"', (ROOT / "scripts" / f).read_text(encoding="utf-8")))
    ok_all = True
    for name in sorted(refs):
        for ext in ("png", "pdf"):
            p = ROOT / "figures" / f"{name}.{ext}"
            ok = p.exists() and p.stat().st_mtime >= newest_result
            ok_all &= ok
            print(f"{'OK ' if ok else 'BAD'} figures/{name}.{ext}")
    return ok_all


if __name__ == "__main__":
    a = check_numbers()
    b = check_figures()
    print("ALL CHECKS PASSED" if a and b else "CHECKS FAILED")
    sys.exit(0 if a and b else 1)
