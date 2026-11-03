"""Phase 1: FLORES-200 evaluation data and the Sangraha training corpus.

Usage: python src/data.py [--per-lang 50000]
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor

import regex

from config import CORPUS_DIR, FLORES_DIR, LANGS, RESULTS, SCRIPT_BLOCKS, SEED

log = logging.getLogger("data")

FLORES_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"
SANGRAHA_FILES = ["data-0.parquet", "data-1.parquet"]
HELDOUT_PER_LANG = 100
WINDOW = 40  # shared normalised substring length that counts as eval overlap
MAX_SENTS_PER_DOC = 20

_SENT_SPLIT = regex.compile(r"(?<=[.!?।॥])\s+")
_URL = regex.compile(r"https?://|www\.|\S+@\S+")
_KEEP = regex.compile(r"[^\p{L}\p{M}\p{N}]+")


def load_flores(split: str = "devtest", langs=None) -> dict[str, list[str]]:
    out = {}
    for lang in langs or LANGS:
        path = FLORES_DIR / split / f"{lang}.{split}"
        out[lang] = path.read_text(encoding="utf-8").splitlines()
    return out


def norm_key(s: str) -> str:
    return _KEEP.sub("", unicodedata.normalize("NFC", s)).lower()


def script_ratio(s: str, script: str) -> float:
    letters = [c for c in s if unicodedata.category(c)[0] in "LM"]
    if not letters:
        return 0.0
    if script == "Latin":
        hit = sum(1 for c in letters if c.isascii())
    else:
        lo, hi = SCRIPT_BLOCKS[script]
        hit = sum(1 for c in letters if lo <= ord(c) <= hi)
    return hit / len(letters)


def split_sentences(doc: str):
    for line in doc.splitlines():
        line = " ".join(line.split())
        if not line:
            continue
        for s in _SENT_SPLIT.split(line):
            yield s.strip()


def keep_sentence(s: str, script: str) -> bool:
    n_words = len(s.split())
    return (20 <= len(s) <= 500 and 4 <= n_words <= 80 and not _URL.search(s)
            and script_ratio(s, script) >= 0.8)


class OverlapFilter:
    """Exact or near-exact (shared 40-char normalised substring) overlap with FLORES."""

    def __init__(self, sentences: list[str]):
        self.keys = set()
        self.windows = set()
        for s in sentences:
            k = norm_key(s)
            self.keys.add(k)
            for i in range(max(1, len(k) - WINDOW + 1)):
                self.windows.add(k[i:i + WINDOW])

    def hit(self, s: str) -> bool:
        k = norm_key(s)
        if k in self.keys:
            return True
        if len(k) < WINDOW:
            return False
        return any(k[i:i + WINDOW] in self.windows for i in range(len(k) - WINDOW + 1))


def _iter_sangraha_docs(code: str):
    import pyarrow.parquet as pq
    from huggingface_hub import HfFileSystem

    fs = HfFileSystem()
    for name in SANGRAHA_FILES:
        path = f"datasets/ai4bharat/sangraha/verified/{code}/{name}"
        with fs.open(path, "rb", block_size=4 * 2**20) as f:
            pf = pq.ParquetFile(f, buffer_size=4 * 2**20, pre_buffer=False)
            for batch in pf.iter_batches(batch_size=256, columns=["text"]):
                yield from batch.column(0).to_pylist()


def _iter_wiki_docs(code: str):
    from datasets import load_dataset
    ds = load_dataset("wikimedia/wikipedia", f"20231101.{code}", split="train", streaming=True)
    for ex in ds:
        yield ex["text"]


def collect_language(lang: str, per_lang: int, flores_sents: list[str]) -> dict:
    meta = LANGS[lang]
    script = meta["script"]
    flt = OverlapFilter(flores_sents)
    need = per_lang + HELDOUT_PER_LANG
    stats = dict(lang=lang, docs=0, candidates=0, filtered_out=0, duplicates=0, eval_overlap=0)
    seen, kept = set(), []
    t0 = time.time()
    sources = [("ai4bharat/sangraha (verified)", _iter_sangraha_docs, meta["sangraha"]),
               ("wikimedia/wikipedia 20231101", _iter_wiki_docs, meta["wiki"])]
    for source, it, code in sources:
        try:
            for doc in it(code):
                stats["docs"] += 1
                for j, s in enumerate(split_sentences(doc)):
                    if j >= MAX_SENTS_PER_DOC:
                        break
                    stats["candidates"] += 1
                    if not keep_sentence(s, script):
                        stats["filtered_out"] += 1
                        continue
                    k = norm_key(s)
                    if k in seen:
                        stats["duplicates"] += 1
                        continue
                    seen.add(k)
                    if flt.hit(s):
                        stats["eval_overlap"] += 1
                        continue
                    kept.append(s)
                if len(kept) >= need:
                    break
            stats["source"] = source
            if len(kept) >= need:
                break
        except Exception as ex:  # noqa: BLE001 - fall back to the next source
            log.warning("%s: %s failed (%s); trying fallback", lang, source, ex)
            stats.setdefault("errors", []).append(f"{source}: {type(ex).__name__}: {ex}")
    rng = random.Random(SEED)
    rng.shuffle(kept)
    held, train = kept[:HELDOUT_PER_LANG], kept[HELDOUT_PER_LANG:need]
    (CORPUS_DIR / f"{lang}.txt").write_text("\n".join(train) + "\n", encoding="utf-8")
    (CORPUS_DIR / f"heldout_{lang}.txt").write_text("\n".join(held) + "\n", encoding="utf-8")
    stats.update(train_sentences=len(train), heldout_sentences=len(held), seconds=round(time.time() - t0, 1))
    log.info("%s: %s", lang, stats)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-lang", type=int, default=50000)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    for noisy in ("httpx", "httpx2", "huggingface_hub", "fsspec"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    flores = {l: load_flores("dev")[l] + load_flores("devtest")[l] for l in LANGS}
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(lambda l: collect_language(l, args.per_lang, flores[l]), LANGS))
    out = {"per_lang_target": args.per_lang, "heldout_per_lang": HELDOUT_PER_LANG,
           "overlap_rule": f"exact normalised match or shared {WINDOW}-char normalised substring "
                           "with FLORES-200 dev+devtest", "languages": results}
    (RESULTS / "corpus_stats.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
