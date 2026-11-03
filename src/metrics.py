"""Phase 3: per-sentence and per-(tokenizer, language) tokenization metrics.

Usage: python src/metrics.py [--workers 4] [--only key ...]
Writes results/sentence_level.csv.gz, results/benchmark_long.csv,
results/benchmark_summary.csv and results/tokenizer_info.csv.
"""
from __future__ import annotations

import argparse
import bisect
import json
import logging
import math
import unicodedata
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import regex

import config
from akshara import akshara_byte_spans, char_to_byte_offsets
from config import CONTEXT_WINDOW, INDIC, LANGS, RESULTS

log = logging.getLogger("metrics")

_WS = regex.compile(r"\S+")
RENYI_ALPHA = 2.5


def _is_punct(ch: str) -> bool:
    return unicodedata.category(ch)[0] in "PS"


def words(text: str) -> list[str]:
    """Whitespace split with punctuation stripped; the same rule for every tokenizer."""
    out = []
    for w in text.split():
        w = "".join(c for c in w if not _is_punct(c))
        if w:
            out.append(w)
    return out


def word_byte_spans(text: str) -> list[tuple[int, int]]:
    """Byte spans of whitespace words with leading/trailing punctuation trimmed."""
    offs = char_to_byte_offsets(text)
    spans = []
    for m in _WS.finditer(text):
        s, e = m.span()
        while s < e and _is_punct(text[s]):
            s += 1
        while e > s and _is_punct(text[e - 1]):
            e -= 1
        if s < e:
            spans.append((offs[s], offs[e]))
    return spans


def codepoint_byte_spans(text: str) -> list[tuple[int, int]]:
    offs = char_to_byte_offsets(text)
    return [(offs[i], offs[i + 1]) for i, ch in enumerate(text) if not ch.isspace()]


def _boundaries(spans: list[tuple[int, int]]) -> list[int]:
    b = set()
    for s, e in spans:
        b.add(s)
        b.add(e)
    return sorted(b)


def _n_split(units: list[tuple[int, int]], bounds: list[int]) -> int:
    """Number of units [s, e) with a token boundary strictly inside them."""
    n = 0
    for s, e in units:
        i = bisect.bisect_right(bounds, s)
        if i < len(bounds) and bounds[i] < e:
            n += 1
    return n


def _n_continued(word_spans, token_spans) -> int:
    starts = [s for s, _ in token_spans]
    n = 0
    for ws, we in word_spans:
        # tokens overlapping [ws, we): those with start < we and end > ws
        hi = bisect.bisect_left(starts, we)
        cnt = 0
        for j in range(hi - 1, -1, -1):
            s, e = token_spans[j]
            if e <= ws:
                break
            cnt += 1
            if cnt >= 2:
                n += 1
                break
    return n


def sentence_metrics(enc, raw: str) -> dict:
    row = dict(n_tokens=enc.n_tokens, n_unk=enc.n_unk, n_words=len(words(raw)), n_chars=len(raw),
               n_bytes=len(raw.encode("utf-8")), span_mode=enc.mode)
    if enc.spans is None:
        row.update(n_aksharas=None, n_split_aksharas=None, n_codepoints=None,
                   n_split_codepoints=None, n_words_spanned=None, n_continued=None)
        return row
    ref = enc.ref_text
    spans = [(s, e) for s, e in enc.spans if e > s]
    bounds = _boundaries(spans)
    # Only interior boundaries can split a unit; drop the text edges.
    total = len(ref.encode("utf-8"))
    bounds = [b for b in bounds if 0 < b < total]
    aks = akshara_byte_spans(ref, indic_only=True)
    cps = codepoint_byte_spans(ref)
    wsp = word_byte_spans(ref)
    row.update(n_aksharas=len(aks), n_split_aksharas=_n_split(aks, bounds),
               n_codepoints=len(cps), n_split_codepoints=_n_split(cps, bounds),
               n_words_spanned=len(wsp), n_continued=_n_continued(wsp, spans))
    return row


def renyi_efficiency(counter: Counter, vocab_size: int, alpha: float = RENYI_ALPHA) -> float:
    total = sum(counter.values())
    if total == 0:
        return float("nan")
    s = sum((c / total) ** alpha for c in counter.values())
    h = math.log(s) / (1 - alpha)
    return h / math.log(vocab_size)


def evaluate_tokenizer(entry) -> tuple[list[dict], dict, dict]:
    """Worker: load one tokenizer and score every FLORES sentence in every language."""
    import os
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from data import load_flores
    from tokenizers_zoo import load
    logging.getLogger("transformers").setLevel(logging.ERROR)
    tok = load(entry)
    flores = load_flores("devtest")
    rows, renyi = [], {}
    for lang, sents in flores.items():
        piece_counts = Counter()
        for sid, raw in enumerate(sents):
            enc = tok.encode(raw)
            r = sentence_metrics(enc, raw)
            r.update(tokenizer=entry.key, lang=lang, sid=sid)
            rows.append(r)
            piece_counts.update(enc.pieces() if enc.spans is not None else [])
        renyi[lang] = renyi_efficiency(piece_counts, tok.vocab_size)
    info = dict(tokenizer=entry.key, label=entry.label, group=entry.group, source=entry.source,
                note=entry.note, family=tok.family, span_mode=tok.span_mode, vocab_size=tok.vocab_size,
                vocab_sha256=tok.vocab_hash())
    if hasattr(tok, "stats"):
        info["span_stats"] = json.dumps(tok.stats)
    return rows, renyi, info


def aggregate(df: pd.DataFrame, renyi: dict) -> pd.DataFrame:
    eng = df[df.lang == "eng_Latn"].set_index(["tokenizer", "sid"])["n_tokens"]
    out = []
    for (tk, lang), g in df.groupby(["tokenizer", "lang"], sort=False):
        e = eng.loc[tk].reindex(g.sid).to_numpy()
        tokens, words_ = g.n_tokens.sum(), g.n_words.sum()
        spanned = g.dropna(subset=["n_aksharas"])
        fert = tokens / words_
        row = dict(
            tokenizer=tk, lang=lang,
            fertility=fert,
            chars_per_token=g.n_chars.sum() / tokens,
            bytes_per_token=g.n_bytes.sum() / tokens,
            parity=tokens / e.sum(),
            parity_sentence_mean=float((g.n_tokens.to_numpy() / e).mean()),
            pcw=spanned.n_continued.sum() / spanned.n_words_spanned.sum() if len(spanned) else float("nan"),
            asr=100 * spanned.n_split_aksharas.sum() / spanned.n_aksharas.sum()
            if len(spanned) and spanned.n_aksharas.sum() else float("nan"),
            intra_char_split=100 * spanned.n_split_codepoints.sum() / spanned.n_codepoints.sum()
            if len(spanned) else float("nan"),
            words_in_8k=CONTEXT_WINDOW / fert,
            cost_multiplier=tokens / e.sum(),
            unk_rate=100 * g.n_unk.sum() / tokens,
            renyi_efficiency=renyi[(tk, lang)],
            span_coverage=len(spanned) / len(g),
            n_sentences=len(g),
        )
        out.append(row)
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", nargs="*", help="tokenizer keys to (re)compute")
    ap.add_argument("--no-local", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    from tokenizers_zoo import ZOO, load_zoo
    from train_tokenizers import local_entries

    # Download / validate every tokenizer once in the parent so skips are logged centrally.
    entries = list(ZOO)
    loaded, skipped = load_zoo(entries)
    entries = [e for e in entries if e.key in loaded]
    # Sarvam-30B and 105B: report a single row if the vocabularies are identical.
    if "sarvam-30b" in loaded and "sarvam-105b" in loaded:
        if loaded["sarvam-30b"].vocab_hash() == loaded["sarvam-105b"].vocab_hash():
            entries = [e for e in entries if e.key != "sarvam-105b"]
            for e in entries:
                if e.key == "sarvam-30b":
                    e.label = "Sarvam-30B/105B"
            skipped["sarvam-105b"] = "identical vocabulary and merges to sarvam-30b (sha256 match); merged row"
    del loaded
    if not args.no_local:
        entries += local_entries()
    if args.only:
        entries = [e for e in entries if e.key in args.only]

    sent_path = RESULTS / "sentence_level.csv.gz"
    old = pd.read_csv(sent_path) if (args.only and sent_path.exists()) else None
    info_path = RESULTS / "tokenizer_info.csv"
    old_info = pd.read_csv(info_path) if (args.only and info_path.exists()) else None
    renyi_path = RESULTS / "renyi.json"
    renyi_all = json.loads(renyi_path.read_text()) if (args.only and renyi_path.exists()) else {}

    rows, infos = [], []
    with ProcessPoolExecutor(args.workers) as pool:
        for r, renyi, info in pool.map(evaluate_tokenizer, entries):
            rows += r
            infos.append(info)
            for lang, v in renyi.items():
                renyi_all[f"{info['tokenizer']}|{lang}"] = v
            log.info("done %s", info["tokenizer"])
    df = pd.DataFrame(rows)
    info_df = pd.DataFrame(infos)
    if old is not None:
        df = pd.concat([old[~old.tokenizer.isin(df.tokenizer.unique())], df], ignore_index=True)
        info_df = pd.concat([old_info[~old_info.tokenizer.isin(info_df.tokenizer)], info_df], ignore_index=True)
    df.to_csv(sent_path, index=False)
    info_df.to_csv(info_path, index=False)
    renyi_path.write_text(json.dumps(renyi_all, indent=1), encoding="utf-8")
    (RESULTS / "skipped_tokenizers.json").write_text(json.dumps(skipped, indent=2), encoding="utf-8")

    renyi = {tuple(k.split("|")): v for k, v in renyi_all.items()}
    summ = aggregate(df, renyi)
    meta = info_df.set_index("tokenizer")
    summ.insert(1, "label", summ.tokenizer.map(meta["label"]))
    summ.insert(2, "group", summ.tokenizer.map(meta["group"]))
    summ.insert(4, "language", summ.lang.map(lambda l: LANGS[l]["name"]))
    summ.insert(5, "lang_family", summ.lang.map(lambda l: LANGS[l]["family"]))
    summ.to_csv(RESULTS / "benchmark_summary.csv", index=False)
    long = summ.melt(id_vars=["tokenizer", "label", "group", "lang", "language", "lang_family"],
                     var_name="metric", value_name="value")
    long.to_csv(RESULTS / "benchmark_long.csv", index=False)
    log.info("wrote %d sentence rows, %d summary rows", len(df), len(summ))


if __name__ == "__main__":
    main()
