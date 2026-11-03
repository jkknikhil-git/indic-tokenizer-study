"""Vocabulary composition: how many vocabulary entries each script gets.

Usage: python src/vocab_analysis.py
Writes results/vocab_composition.csv and results/vocab_indic_share.csv.
"""
from __future__ import annotations

import json
import logging
import os
import unicodedata
from collections import Counter, defaultdict

import pandas as pd

from akshara import aksharas, is_indic_unit, script_of
from config import RESULTS

log = logging.getLogger("vocab")
BRAHMIC = ["Devanagari", "Bengali", "Gurmukhi", "Gujarati", "Oriya", "Tamil", "Telugu", "Kannada", "Malayalam"]


def char_script(ch: str) -> str | None:
    s = script_of(ch)
    if s:
        return s
    cat = unicodedata.category(ch)
    if cat[0] not in "LM":
        return None
    name = unicodedata.name(ch, "")
    for prefix, label in (("MEETEI MAYEK", "Meetei Mayek"), ("OL CHIKI", "Ol Chiki"), ("TIBETAN", "Tibetan"),
                          ("LATIN", "Latin"), ("CJK", "CJK"), ("HIRAGANA", "CJK"), ("KATAKANA", "CJK"),
                          ("HANGUL", "CJK"), ("CYRILLIC", "Cyrillic"), ("ARABIC", "Arabic"),
                          ("GREEK", "Greek"), ("HEBREW", "Hebrew"), ("THAI", "Thai")):
        if name.startswith(prefix):
            return label
    if cat[0] == "M":
        return None  # stray combining mark: decided by its neighbours
    return "Other"


def classify(piece: bytes, special: bool = False) -> tuple[str, str]:
    """Return (script class, decoded text) for one vocabulary entry."""
    if special:
        return "Special", ""
    try:
        text = piece.decode("utf-8")
    except UnicodeDecodeError:
        return "Partial byte sequence", ""
    core = text.replace("▁", " ").strip()
    if core.startswith("##"):
        core = core[2:]
    scripts = {s for s in (char_script(c) for c in core) if s}
    if not scripts:
        return ("Digits/Symbols" if core else "Whitespace"), core
    if len(scripts) > 1:
        return "Mixed", core
    return scripts.pop(), core


def analyse(key: str, tok) -> list[dict]:
    special = getattr(tok, "added", set())
    entries = []
    if hasattr(tok, "vocab") and isinstance(getattr(tok, "vocab"), dict):
        for t in tok.vocab:
            entries.append((tok._piece_bytes(t), t in special))
    else:
        entries = [(b, False) for b in tok.vocab_bytes()]
    counts, ak_len = Counter(), defaultdict(list)
    for b, sp in entries:
        cls, core = classify(b, sp)
        counts[cls] += 1
        if cls in BRAHMIC:
            ak_len[cls].append(sum(1 for a in aksharas(core) if is_indic_unit(a)))
    total = sum(counts.values())
    rows = []
    for cls, n in counts.items():
        lens = ak_len.get(cls, [])
        rows.append(dict(tokenizer=key, script=cls, n_tokens=n, pct=100 * n / total,
                         mean_aksharas=sum(lens) / len(lens) if lens else None, vocab_total=total))
    return rows


def compare_vocabs(a, b, name_a: str, name_b: str) -> dict:
    """How much of tokenizer ``a``'s vocabulary is inherited from ``b`` (same string and id)."""
    va, vb = a.vocab, b.vocab
    only_a = [t for t in va if t not in vb]
    only_b = [t for t in vb if t not in va]
    return dict(
        a=name_a, b=name_b, vocab_a=len(va), vocab_b=len(vb),
        shared_strings=len(set(va) & set(vb)),
        shared_string_and_id=sum(1 for t, i in va.items() if vb.get(t) == i),
        only_in_a=len(only_a), only_in_b=len(only_b),
        only_in_a_by_script=dict(Counter(classify(a._piece_bytes(t))[0] for t in only_a).most_common()),
        only_in_b_by_script=dict(Counter(classify(b._piece_bytes(t))[0] for t in only_b).most_common()),
    )


def lineage(loaded: dict) -> list[dict]:
    """Sarvam-30B vs Gemma-3, and Sarvam-M vs the Mistral-Small-3.1 tokenizer it was built on."""
    from tokenizers_zoo import HFTokenizer, ZooEntry
    out = []
    if "sarvam-30b" in loaded and "gemma-3" in loaded:
        out.append(compare_vocabs(loaded["sarvam-30b"], loaded["gemma-3"], "Sarvam-30B/105B", "Gemma-3"))
    if "sarvam-m" in loaded:
        # unsloth's tokenizer.json has the same git blob id as mistralai/Mistral-Small-3.1-24B-Instruct-2503
        # (4135d4bb...), so the ungated copy is byte-identical to the official file.
        try:
            mistral = HFTokenizer(ZooEntry("mistral-small-3.1", "Mistral-Small-3.1",
                                           "unsloth/Mistral-Small-3.1-24B-Instruct-2503", "Reference", "hf"))
            out.append(compare_vocabs(loaded["sarvam-m"], mistral, "Sarvam-M", "Mistral-Small-3.1 (Tekken)"))
        except Exception as ex:  # noqa: BLE001
            out.append(dict(a="Sarvam-M", b="Mistral-Small-3.1", error=str(ex)))
    return out


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    from tokenizers_zoo import ZOO, load
    from train_tokenizers import local_entries
    info = pd.read_csv(RESULTS / "tokenizer_info.csv")
    keep = set(info.tokenizer)
    rows, loaded = [], {}
    for e in list(ZOO) + local_entries():
        if e.key not in keep and e.key != "gemma-3":
            continue
        tok = load(e)
        loaded[e.key] = tok
        if e.key in keep:
            rows += analyse(e.key, tok)
        log.info("analysed %s", e.key)
    (RESULTS / "vocab_lineage.json").write_text(json.dumps(lineage(loaded), indent=2, ensure_ascii=False),
                                                encoding="utf-8")
    df = pd.DataFrame(rows)
    df["label"] = df.tokenizer.map(info.set_index("tokenizer")["label"])
    df.to_csv(RESULTS / "vocab_composition.csv", index=False)
    share = (df[df.script.isin(BRAHMIC)].groupby("tokenizer")
             .agg(indic_tokens=("n_tokens", "sum"), indic_pct=("pct", "sum")).reset_index())
    share["label"] = share.tokenizer.map(info.set_index("tokenizer")["label"])
    share.to_csv(RESULTS / "vocab_indic_share.csv", index=False)


if __name__ == "__main__":
    main()
