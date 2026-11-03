"""Phase 4 (RQ4): standard BPE, akshara-atomic BPE and a Unigram baseline.

Akshara-atomic BPE
------------------
1. Segment the training corpus into aksharas (``akshara.py``).
2. Map every Indic akshara type with frequency >= 2 to its own Supplementary
   Private Use Area-A codepoint (U+F0000 onwards). The inventory is capped at the
   ``floor(V * MAP_FRACTION)`` most frequent aksharas so that base symbols never
   crowd out merges (21.7K types exceed a 16K vocabulary). Rarer aksharas stay as
   raw characters.
3. Train SentencePiece BPE on the mapped text. Merges can join aksharas but can
   never split a mapped one. ``encode``/``decode`` apply and reverse the mapping.

All variants share the same SentencePiece options (identity normalisation,
character_coverage=1.0, byte_fallback, split_by_unicode_script=False).

Usage: python src/train_tokenizers.py [--sizes 16000 32000 64000] [--unigram 64000]
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import time
from collections import Counter
from pathlib import Path

import sentencepiece as spm

from akshara import akshara_spans, is_indic_unit
from config import CORPUS_DIR, LANGS, MODELS_DIR, RESULTS, SEED
from tokenizers_zoo import Encoded, ZooEntry

log = logging.getLogger("train")

PUA_START = 0xF0000
PUA_END = 0xFFFFD
MIN_FREQ = 2
MAP_FRACTION = 0.5
META = "▁"
_SP_BYTE = re.compile(r"^<0x([0-9A-Fa-f]{2})>$")

SP_COMMON = dict(
    character_coverage=1.0,
    byte_fallback=True,
    normalization_rule_name="identity",
    remove_extra_whitespaces=False,
    split_by_unicode_script=False,
    split_digits=True,
    max_sentence_length=8192,
    shuffle_input_sentence=True,
    input_sentence_size=0,
    num_threads=8,
    seed_sentencepiece_size=1_000_000,
    unk_id=0, bos_id=-1, eos_id=-1, pad_id=-1,
)


def corpus_files() -> list[Path]:
    return [CORPUS_DIR / f"{l}.txt" for l in LANGS]


def iter_corpus():
    for f in corpus_files():
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if line:
                    yield line


def count_aksharas() -> Counter:
    c = Counter()
    for line in iter_corpus():
        c.update(line[s:e] for s, e in akshara_spans(line) if is_indic_unit(line[s:e]))
    return c


class AksharaMapper:
    def __init__(self, table: dict[str, str]):
        self.fwd = table  # akshara -> PUA char
        self.inv = {v: k for k, v in table.items()}

    @classmethod
    def build(cls, counts: Counter, cap: int) -> "AksharaMapper":
        frequent = [a for a, n in counts.most_common() if n >= MIN_FREQ][:cap]
        assert len(frequent) <= PUA_END - PUA_START + 1
        return cls({a: chr(PUA_START + i) for i, a in enumerate(frequent)})

    @classmethod
    def load(cls, path: Path) -> "AksharaMapper":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path):
        path.write_text(json.dumps(self.fwd, ensure_ascii=False, indent=0), encoding="utf-8")

    def map(self, text: str) -> str:
        fwd = self.fwd
        return "".join(fwd.get(text[s:e], text[s:e]) for s, e in akshara_spans(text))

    def unmap(self, text: str) -> str:
        inv = self.inv
        return "".join(inv.get(ch, ch) for ch in text)


class LocalSPTokenizer:
    """A SentencePiece model trained here, optionally behind an akshara mapping."""

    def __init__(self, entry: ZooEntry):
        self.entry = entry
        path = Path(entry.source)
        self.sp = spm.SentencePieceProcessor(model_file=str(path))
        mp = path.with_suffix(".akshara.json")
        self.mapper = AksharaMapper.load(mp) if mp.exists() else None
        self.vocab_size = self.sp.get_piece_size()
        kind = entry.extra.get("algo", "bpe")
        self.family = f"SentencePiece {kind}" + (" (akshara-atomic)" if self.mapper else "")
        self.span_mode = "bytes"

    def _piece_bytes(self, piece: str) -> bytes:
        m = _SP_BYTE.match(piece)
        if m:
            return bytes([int(m.group(1), 16)])
        if self.mapper:
            piece = self.mapper.unmap(piece)
        return piece.replace("▁", " ").encode("utf-8")

    def encode_pieces(self, text: str) -> list[str]:
        return self.sp.encode(self.mapper.map(text) if self.mapper else text, out_type=str)

    def encode(self, text: str) -> Encoded:
        pieces = self.encode_pieces(text)
        unk = sum(1 for pc in pieces if pc == "<unk>")
        bts = [self._piece_bytes(p) for p in pieces]
        target = text.encode("utf-8")
        if b"".join(bts) == b" " + target and bts and bts[0].startswith(b" "):
            bts[0] = bts[0][1:]
        spans, p = [], 0
        for b in bts:
            spans.append((p, p + len(b)))
            p += len(b)
        ok = b"".join(bts) == target
        return Encoded(len(pieces), text, spans if ok else None, "bytes" if ok else "none", unk)

    def decode(self, text_ids_or_pieces) -> str:
        out = self.sp.decode(text_ids_or_pieces)
        return self.mapper.unmap(out) if self.mapper else out

    def roundtrip(self, text: str) -> str:
        return self.decode(self.sp.encode(self.mapper.map(text) if self.mapper else text))

    def vocab_bytes(self) -> list[bytes]:
        return [self._piece_bytes(self.sp.id_to_piece(i)) for i in range(self.vocab_size)
                if not (self.sp.is_unknown(i) or self.sp.is_control(i))]

    def vocab_hash(self) -> str:
        import hashlib
        return hashlib.sha256(Path(self.entry.source).read_bytes()).hexdigest()


def model_name(algo: str, atomic: bool, size: int) -> str:
    return f"ours-{'akshara-' if atomic else ''}{algo}-{size // 1000}k"


def local_entries() -> list[ZooEntry]:
    out = []
    for path in sorted(MODELS_DIR.glob("ours-*.model")):
        name = path.stem
        atomic = "akshara" in name
        algo = "unigram" if "unigram" in name else "bpe"
        size = name.rsplit("-", 1)[1].upper()
        label = f"Ours {'Akshara-BPE' if atomic else ('Unigram' if algo == 'unigram' else 'BPE')} {size}"
        out.append(ZooEntry(name, label, str(path), "Ours", "local", extra={"algo": algo, "size": size}))
    return out


def train_one(algo: str, size: int, atomic: bool, counts: Counter | None) -> dict:
    name = model_name(algo, atomic, size)
    prefix = MODELS_DIR / name
    t0 = time.time()
    info = dict(name=name, algo=algo, vocab_size=size, akshara_atomic=atomic)
    if atomic:
        cap = int(size * MAP_FRACTION)
        mapper = AksharaMapper.build(counts, cap)
        mapper.save(prefix.with_suffix(".akshara.json"))
        total = sum(counts.values())
        info.update(mapped_types=len(mapper.fwd), map_cap=cap,
                    token_coverage=round(sum(counts[a] for a in mapper.fwd) / total, 5))
        mapped = MODELS_DIR / f"{name}.train_mapped.txt"
        with mapped.open("w", encoding="utf-8") as fh:
            for line in iter_corpus():
                fh.write(mapper.map(line) + "\n")
        inputs = [str(mapped)]
        info["mapping_seconds"] = round(time.time() - t0, 1)
    else:
        inputs = [str(f) for f in corpus_files()]
    spm.set_random_generator_seed(SEED)
    t1 = time.time()
    spm.SentencePieceTrainer.train(input=inputs, model_prefix=str(prefix), model_type=algo,
                                   vocab_size=size, minloglevel=1, **SP_COMMON)
    info["train_seconds"] = round(time.time() - t1, 1)
    info["total_seconds"] = round(time.time() - t0, 1)
    if atomic:
        Path(inputs[0]).unlink(missing_ok=True)
    log.info("%s", info)
    return info


def akshara_coverage() -> dict:
    """Where do the residual akshara splits of the akshara-atomic models come from?

    For each model: share of FLORES devtest Indic aksharas outside its mapping inventory, and how
    many split aksharas were mapped (should be 0) vs unmapped.
    """
    from akshara import char_to_byte_offsets
    from config import INDIC
    from data import load_flores
    flores = load_flores("devtest", INDIC)
    out = {}
    for entry in [e for e in local_entries() if "akshara" in e.key]:
        tok = LocalSPTokenizer(entry)
        tot = oov = split_mapped = split_unmapped = 0
        for lang in INDIC:
            for s in flores[lang]:
                enc = tok.encode(s)
                starts = {a for a, _ in enc.spans}
                offs = char_to_byte_offsets(s)
                for a, b in akshara_spans(s):
                    unit = s[a:b]
                    if not is_indic_unit(unit):
                        continue
                    tot += 1
                    mapped = unit in tok.mapper.fwd
                    oov += not mapped
                    if any(offs[a] < x < offs[b] for x in starts):
                        if mapped:
                            split_mapped += 1
                        else:
                            split_unmapped += 1
        out[entry.key] = dict(aksharas=tot, outside_inventory=oov, outside_inventory_pct=100 * oov / tot,
                              split_mapped=split_mapped, split_unmapped=split_unmapped,
                              asr_pct=100 * (split_mapped + split_unmapped) / tot)
    # Standalone word-boundary pieces: SentencePiece emits a bare meta-symbol when no merge joins it to the
    # first symbol of a word, which happens more often once that symbol is an atomic akshara.
    for entry in local_entries():
        tok = LocalSPTokenizer(entry)
        n_tok = n_bare = 0
        for lang in INDIC:
            for s in flores[lang]:
                pieces = tok.encode_pieces(s)
                n_tok += len(pieces)
                n_bare += sum(1 for pc in pieces if pc == META)
        out.setdefault(entry.key, {}).update(tokens=n_tok, bare_metaspace=n_bare)
    (RESULTS / "akshara_coverage.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage-only", action="store_true", help="only analyse akshara inventory coverage")
    ap.add_argument("--sizes", type=int, nargs="+", default=[16000, 32000, 64000])
    ap.add_argument("--unigram", type=int, nargs="*", default=[64000])
    ap.add_argument("--only", choices=["bpe", "akshara", "unigram"], nargs="*")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if args.coverage_only:
        log.info("%s", akshara_coverage())
        return
    only = set(args.only or ["bpe", "akshara", "unigram"])
    log_path = RESULTS / "training_log.json"
    runs = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}
    counts = None
    if "akshara" in only:
        t = time.time()
        counts = count_aksharas()
        log.info("counted %d akshara types in %.1fs", len(counts), time.time() - t)
        runs["_akshara_inventory"] = dict(
            types=len(counts), types_freq_ge2=sum(1 for v in counts.values() if v >= MIN_FREQ),
            tokens=sum(counts.values()))
    jobs = []
    for size in args.sizes:
        if "bpe" in only:
            jobs.append(("bpe", size, False))
        if "akshara" in only:
            jobs.append(("bpe", size, True))
    if "unigram" in only:
        jobs += [("unigram", size, False) for size in args.unigram]
    for algo, size, atomic in jobs:
        info = train_one(algo, size, atomic, counts)
        runs[info["name"]] = info
        log_path.write_text(json.dumps(runs, indent=2), encoding="utf-8")
    if "akshara" in only:
        akshara_coverage()


if __name__ == "__main__":
    main()
