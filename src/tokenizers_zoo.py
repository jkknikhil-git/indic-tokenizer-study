"""Common interface over tiktoken, Hugging Face and local SentencePiece tokenizers.

Every tokenizer exposes ``encode(text) -> Encoded`` where ``Encoded.spans`` are the
exact UTF-8 byte spans of each token inside ``Encoded.ref_text`` (the text the
tokenizer actually saw after its own normalisation). Three span adapters exist:

* ``bytes``    - token -> raw bytes (tiktoken, HF byte-level BPE, SentencePiece with
                 byte fallback). Concatenation must equal the normalised input.
* ``offsets``  - HF character offsets into the original text (WordPiece, Unigram
                 without byte fallback). Validated by monotonicity and coverage of
                 every non-whitespace character.
* ``none``     - only token counts are trusted (akshara metrics become N/A).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field

import config  # noqa: F401  (sets HF_HOME before transformers is imported)
from akshara import char_to_byte_offsets

log = logging.getLogger(__name__)


@dataclass
class Encoded:
    n_tokens: int
    ref_text: str
    spans: list[tuple[int, int]] | None  # byte spans into ref_text.encode("utf-8")
    mode: str  # "bytes" | "offsets" | "none"

    def pieces(self) -> list[str]:
        b = self.ref_text.encode("utf-8")
        return [b[s:e].decode("utf-8", errors="replace") for s, e in (self.spans or [])]


@dataclass
class ZooEntry:
    key: str
    label: str
    source: str  # repo id / encoding name
    group: str  # "Sarvam" | "Proprietary" | "Open LLM" | "Encoder" | "Ours"
    loader: str  # "hf" | "tiktoken" | "local"
    note: str = ""
    extra: dict = field(default_factory=dict)


ZOO: list[ZooEntry] = [
    ZooEntry("sarvam-1", "Sarvam-1", "sarvamai/sarvam-1", "Sarvam", "hf"),
    ZooEntry("sarvam-m", "Sarvam-M", "sarvamai/sarvam-m", "Sarvam", "hf"),
    ZooEntry("sarvam-30b", "Sarvam-30B", "sarvamai/sarvam-30b", "Sarvam", "hf"),
    ZooEntry("sarvam-105b", "Sarvam-105B", "sarvamai/sarvam-105b", "Sarvam", "hf"),
    ZooEntry("gpt-4o", "GPT-4o (o200k)", "o200k_base", "Proprietary", "tiktoken"),
    ZooEntry("gpt-4", "GPT-4 (cl100k)", "cl100k_base", "Proprietary", "tiktoken"),
    ZooEntry("llama-3.1", "Llama-3.1", "unsloth/Llama-3.1-8B", "Open LLM", "hf",
             note="mirror of meta-llama/Llama-3.1-8B", extra={"official": "meta-llama/Llama-3.1-8B"}),
    ZooEntry("gemma-3", "Gemma-3", "unsloth/gemma-3-1b-it", "Open LLM", "hf",
             note="mirror of google/gemma-3-1b-it", extra={"official": "google/gemma-3-1b-it"}),
    ZooEntry("qwen-2.5", "Qwen2.5", "Qwen/Qwen2.5-7B", "Open LLM", "hf"),
    ZooEntry("muril", "MuRIL", "google/muril-base-cased", "Encoder", "hf"),
    ZooEntry("indicbert-v2", "IndicBERTv2", "ai4bharat/IndicBERTv2-MLM-only", "Encoder", "hf"),
    ZooEntry("xlm-r", "XLM-R", "FacebookAI/xlm-roberta-base", "Encoder", "hf"),
    ZooEntry("mbert", "mBERT", "google-bert/bert-base-multilingual-cased", "Encoder", "hf"),
]

_SP_BYTE = re.compile(r"^<0x([0-9A-Fa-f]{2})>$")


def _bytes_to_unicode() -> dict[int, str]:
    """GPT-2 byte <-> printable unicode map used by byte-level BPE."""
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("\xa1"), ord("\xac") + 1)) + list(
        range(ord("\xae"), ord("\xff") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return dict(zip(bs, (chr(c) for c in cs)))


_BYTE_DECODER = {v: k for k, v in _bytes_to_unicode().items()}


def _spans_from_pieces(pieces: list[bytes]) -> list[tuple[int, int]]:
    spans, p = [], 0
    for pc in pieces:
        spans.append((p, p + len(pc)))
        p += len(pc)
    return spans


def _strip_prefix_space(pieces: list[bytes], target: bytes) -> list[bytes] | None:
    """Make concat(pieces) == target, allowing one added leading space (dummy prefix)."""
    joined = b"".join(pieces)
    if joined == target:
        return pieces
    if joined == b" " + target and pieces and pieces[0].startswith(b" "):
        return [pieces[0][1:]] + pieces[1:]
    return None


class TiktokenTokenizer:
    def __init__(self, entry: ZooEntry):
        import tiktoken
        self.entry = entry
        self.enc = tiktoken.get_encoding(entry.source)
        self.vocab_size = self.enc.n_vocab
        self.family = "tiktoken byte-level BPE"
        self.span_mode = "bytes"

    def encode(self, text: str) -> Encoded:
        ids = self.enc.encode(text, disallowed_special=())
        pieces = [self.enc.decode_single_token_bytes(i) for i in ids]
        assert b"".join(pieces) == text.encode("utf-8")
        return Encoded(len(ids), text, _spans_from_pieces(pieces), "bytes")

    def vocab_bytes(self) -> list[bytes]:
        out = []
        for i in range(self.enc.n_vocab):
            try:
                out.append(self.enc.decode_single_token_bytes(i))
            except KeyError:
                pass
        return out

    def vocab_hash(self) -> str:
        return hashlib.sha256(b"\x00".join(self.vocab_bytes())).hexdigest()


class HFTokenizer:
    def __init__(self, entry: ZooEntry):
        from transformers import AutoTokenizer
        self.entry = entry
        self.tok = AutoTokenizer.from_pretrained(entry.source)
        self.backend = self.tok.backend_tokenizer
        spec = json.loads(self.backend.to_str())
        self.spec = spec
        model = spec["model"]
        self.model_type = model["type"]
        self.byte_fallback = bool(model.get("byte_fallback", False))
        blob = json.dumps({k: spec.get(k) for k in ("pre_tokenizer", "decoder", "normalizer")}, ensure_ascii=False)
        self.byte_level = '"ByteLevel"' in blob
        self.metaspace = '"Metaspace"' in blob or "▁" in blob
        self.added = {t.content for t in self.tok.added_tokens_decoder.values()}
        self.vocab = self.backend.get_vocab(with_added_tokens=True)
        self.vocab_size = len(self.vocab)
        if self.byte_level:
            self.family, self.span_mode = f"byte-level {self.model_type}", "bytes"
        elif self.metaspace and self.model_type in ("BPE", "Unigram"):
            fb = "+byte-fallback" if self.byte_fallback else ""
            self.family = f"SentencePiece {self.model_type}{fb}"
            self.span_mode = "bytes" if self.byte_fallback else "offsets"
        else:
            self.family, self.span_mode = self.model_type, "offsets"
        self.normalizer = self.backend.normalizer
        self.stats = {"bytes_ok": 0, "offsets_ok": 0, "failed": 0}

    # ---- helpers -------------------------------------------------------------------
    def normalize(self, text: str) -> str:
        if self.normalizer is None:
            return text
        out = self.normalizer.normalize_str(text)
        if self.metaspace:
            out = out.replace("▁", " ")
            if out.startswith(" ") and not text.startswith(" "):
                out = out[1:]
        return out

    def _piece_bytes(self, tok: str) -> bytes:
        if tok in self.added:
            return (tok.replace("▁", " ") if self.metaspace else tok).encode("utf-8")
        if self.byte_level:
            try:
                return bytes(_BYTE_DECODER[c] for c in tok)
            except KeyError:
                return tok.encode("utf-8")
        m = _SP_BYTE.match(tok)
        if m:
            return bytes([int(m.group(1), 16)])
        return tok.replace("▁", " ").encode("utf-8")

    def _bytes_spans(self, tokens: list[str], ref: str):
        pieces = [self._piece_bytes(t) for t in tokens]
        fixed = _strip_prefix_space(pieces, ref.encode("utf-8"))
        return None if fixed is None else _spans_from_pieces(fixed)

    @staticmethod
    def _offset_spans(text: str, tokens, offsets) -> list[tuple[int, int]] | None:
        boff = char_to_byte_offsets(text)
        spans, last = [], 0
        covered = [False] * len(text)
        for tok, (s, e) in zip(tokens, offsets):
            # A bare "▁" token (XLM-R) carries no text of its own; its offsets point into the next word.
            if e <= s or not tok.strip("▁"):
                continue
            if s < last:  # overlapping tokens: not a clean segmentation
                return None
            spans.append((boff[s], boff[e]))
            for i in range(s, e):
                covered[i] = True
            last = e
        # Normalisers may delete format characters (ZWJ/ZWNJ/ZWSP); everything else must be covered.
        if any(not c and not text[i].isspace() and unicodedata.category(text[i]) != "Cf"
               for i, c in enumerate(covered)):
            return None
        return spans

    # ---- public --------------------------------------------------------------------
    def encode(self, text: str) -> Encoded:
        enc = self.backend.encode(text, add_special_tokens=False)
        n = len(enc.ids)
        if self.span_mode == "bytes":
            ref = self.normalize(text)
            spans = self._bytes_spans(enc.tokens, ref)
            if spans is not None:
                self.stats["bytes_ok"] += 1
                return Encoded(n, ref, spans, "bytes")
        spans = self._offset_spans(text, enc.tokens, enc.offsets)
        if spans is not None:
            self.stats["offsets_ok"] += 1
            return Encoded(n, text, spans, "offsets")
        self.stats["failed"] += 1
        return Encoded(n, text, None, "none")

    def vocab_bytes(self) -> list[bytes]:
        return [self._piece_bytes(t) for t in self.vocab]

    def vocab_hash(self) -> str:
        items = sorted(self.vocab.items(), key=lambda kv: kv[1])
        h = hashlib.sha256(json.dumps(items, ensure_ascii=False).encode("utf-8"))
        h.update(json.dumps(self.spec.get("model", {}).get("merges", []), ensure_ascii=False).encode("utf-8"))
        return h.hexdigest()


def load(entry: ZooEntry):
    if entry.loader == "tiktoken":
        return TiktokenTokenizer(entry)
    if entry.loader == "hf":
        return HFTokenizer(entry)
    if entry.loader == "local":
        from train_tokenizers import LocalSPTokenizer
        return LocalSPTokenizer(entry)
    raise ValueError(entry.loader)


def load_zoo(entries=None):
    """Load every tokenizer, skipping (and logging) the ones that fail."""
    loaded, skipped = {}, {}
    for e in entries or ZOO:
        try:
            loaded[e.key] = load(e)
            log.info("loaded %s (%s, vocab=%d)", e.key, loaded[e.key].family, loaded[e.key].vocab_size)
        except Exception as ex:  # noqa: BLE001 - any failure means "skip and log"
            skipped[e.key] = f"{type(ex).__name__}: {ex}"
            log.warning("skipped %s: %s", e.key, skipped[e.key])
    return loaded, skipped
