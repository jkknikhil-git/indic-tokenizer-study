"""Akshara (orthographic syllable) segmentation for Brahmic scripts.

Algorithm
---------
1. Split text into extended grapheme clusters (``regex`` ``\\X``).
2. Merge a cluster into the following one when it ends in a virama
   (canonical combining class 9), optionally followed by ZWJ/ZWNJ, and the
   following cluster starts with a consonant of the same script. This makes
   conjuncts such as क्ष, ద్ర, ಕ್ಕ one akshara regardless of whether the
   installed Unicode version already joins them inside ``\\X``.

Per-script rules (``SCRIPT_RULES``):
* Tamil: the pulli (U+0BCD) is a visible dead-consonant marker, so by default
  க் + க stays two aksharas (``join_virama=False``). The conjunct க்ஷ (ksha)
  is listed in ``always_join`` and is kept whole.
* Malayalam: chillus are standalone. Atomic chillus (U+0D7A..U+0D7F) are
  letters without a virama and never join. The legacy encoding
  consonant + virama + ZWJ also produces a chillu and is kept standalone
  (``zwj_terminates=True``).

Everything is exposed as spans so token boundaries can be compared directly.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

import regex

from config import SCRIPT_BLOCKS

ZWJ = "‍"
ZWNJ = "‌"
_GRAPHEME = regex.compile(r"\X")

_VOWEL_TAILS = {
    "A", "AA", "I", "II", "U", "UU", "E", "EE", "AI", "O", "OO", "AU",
    "VOCALIC R", "VOCALIC RR", "VOCALIC L", "VOCALIC LL", "SHORT E", "SHORT O",
    "CANDRA E", "CANDRA O", "SHORT A", "OE", "OOE", "AW", "UE", "UUE", "CANDRA A",
}


@dataclass(frozen=True)
class ScriptRule:
    join_virama: bool = True
    zwj_terminates: bool = False
    # (dead consonant cluster, next consonant) pairs that join even if join_virama is False.
    always_join: frozenset = field(default_factory=frozenset)


SCRIPT_RULES: dict[str, ScriptRule] = {
    "Devanagari": ScriptRule(),
    "Bengali": ScriptRule(),
    "Gurmukhi": ScriptRule(),
    "Gujarati": ScriptRule(),
    "Oriya": ScriptRule(),
    "Tamil": ScriptRule(join_virama=False, always_join=frozenset({("க்", "ஷ")})),
    "Telugu": ScriptRule(),
    "Kannada": ScriptRule(),
    "Malayalam": ScriptRule(zwj_terminates=True),
}


@lru_cache(maxsize=8192)
def script_of(ch: str) -> str | None:
    cp = ord(ch)
    for name, (lo, hi) in SCRIPT_BLOCKS.items():
        if lo <= cp <= hi:
            return name
    return None


@lru_cache(maxsize=8192)
def is_virama(ch: str) -> bool:
    return unicodedata.combining(ch) == 9 and script_of(ch) is not None


@lru_cache(maxsize=8192)
def is_consonant(ch: str) -> bool:
    """Brahmic consonant letter (not an independent vowel, not a chillu)."""
    if script_of(ch) is None:
        return False
    name = unicodedata.name(ch, "")
    if " LETTER " not in name or "CHILLU" in name:
        return False
    return name.split(" LETTER ", 1)[1] not in _VOWEL_TAILS


def _dead_consonant(cluster: str, rules: dict[str, ScriptRule]):
    """If ``cluster`` ends in a joining virama, return (script, rule); else None."""
    s = cluster
    zw = None
    if s and s[-1] in (ZWJ, ZWNJ):
        zw, s = s[-1], s[:-1]
    if not s or not is_virama(s[-1]):
        return None
    script = script_of(s[-1])
    rule = rules.get(script, ScriptRule())
    if zw == ZWJ and rule.zwj_terminates:
        return None
    return script, rule


def _base_clusters(text: str):
    """Grapheme clusters, re-split at every virama(+ZWJ/ZWNJ) -> consonant point.

    Newer Unicode versions (GB9c) already join some conjuncts inside ``\\X``; splitting
    them back makes the joining decision ours alone and independent of the Unicode version.
    """
    for m in _GRAPHEME.finditer(text):
        start, end = m.span()
        cut = start
        for i in range(start + 1, end):
            if not is_consonant(text[i]):
                continue
            j = i - 1
            if text[j] in (ZWJ, ZWNJ):
                j -= 1
            if j > cut - 1 and j >= start and is_virama(text[j]):
                yield text[cut:i], cut, i
                cut = i
        yield text[cut:end], cut, end


def akshara_spans(text: str, rules: dict[str, ScriptRule] | None = None) -> list[tuple[int, int]]:
    """Character spans [start, end) of aksharas (or plain grapheme clusters) covering ``text``."""
    rules = SCRIPT_RULES if rules is None else rules
    out: list[list[int]] = []
    prev = None  # (cluster text, script, rule) when the previous cluster ended in a virama
    for cl, start, end in _base_clusters(text):
        joined = False
        if prev is not None and out:
            pcl, pscript, prule = prev
            head = cl[0]
            if is_consonant(head) and script_of(head) == pscript:
                tail = text[out[-1][0]:out[-1][1]]
                if prule.join_virama or any(tail.endswith(a) and head == b for a, b in prule.always_join):
                    out[-1][1] = end
                    joined = True
        if not joined:
            out.append([start, end])
        dead = _dead_consonant(cl, rules)
        prev = (cl, dead[0], dead[1]) if dead else None
    return [(s, e) for s, e in out]


def aksharas(text: str, rules: dict[str, ScriptRule] | None = None) -> list[str]:
    return [text[s:e] for s, e in akshara_spans(text, rules)]


def is_indic_unit(unit: str) -> bool:
    return any(script_of(c) is not None for c in unit)


def char_to_byte_offsets(text: str) -> list[int]:
    """offsets[i] = UTF-8 byte offset of char i; offsets[len(text)] = total bytes."""
    offs = [0] * (len(text) + 1)
    b = 0
    for i, ch in enumerate(text):
        offs[i] = b
        b += len(ch.encode("utf-8"))
    offs[len(text)] = b
    return offs


def akshara_byte_spans(text: str, indic_only: bool = True) -> list[tuple[int, int]]:
    """UTF-8 byte spans of aksharas; with ``indic_only`` non-Brahmic clusters are dropped."""
    offs = char_to_byte_offsets(text)
    return [
        (offs[s], offs[e])
        for s, e in akshara_spans(text)
        if not indic_only or is_indic_unit(text[s:e])
    ]
