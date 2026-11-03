"""Unit tests for the metric helpers, using hand-built token spans."""
import math
from collections import Counter

from metrics import (_boundaries, _n_continued, _n_split, renyi_efficiency, sentence_metrics,
                     word_byte_spans, words)
from tokenizers_zoo import Encoded


def _enc(text, pieces):
    """Encoded object from a list of string pieces whose concatenation is ``text``."""
    spans, p = [], 0
    for pc in pieces:
        n = len(pc.encode("utf-8"))
        spans.append((p, p + n))
        p += n
    assert "".join(pieces) == text
    return Encoded(len(pieces), text, spans, "bytes")


def test_words_strip_punctuation():
    assert words("नमस्ते, दुनिया। ( ) hello!") == ["नमस्ते", "दुनिया", "hello"]


def test_word_spans_trim_punct():
    text = "(ab) c"
    assert word_byte_spans(text) == [(1, 3), (5, 6)]


def test_akshara_split_detected():
    # क्ष is one akshara; splitting after the virama breaks it.
    text = "क्षमा"
    whole = sentence_metrics(_enc(text, ["क्ष", "मा"]), text)
    broken = sentence_metrics(_enc(text, ["क्", "षमा"]), text)
    assert whole["n_aksharas"] == 2 and whole["n_split_aksharas"] == 0
    assert broken["n_split_aksharas"] == 1
    assert broken["n_split_codepoints"] == 0


def test_intra_character_split():
    text = "क"  # 3 UTF-8 bytes
    enc = Encoded(2, text, [(0, 1), (1, 3)], "bytes")
    r = sentence_metrics(enc, text)
    assert r["n_split_codepoints"] == 1 and r["n_split_aksharas"] == 1


def test_continued_words():
    text = "ab cd"
    enc = _enc(text, ["a", "b", " cd"])
    r = sentence_metrics(enc, text)
    assert r["n_words"] == 2 and r["n_continued"] == 1


def test_offset_spans_with_gaps():
    # WordPiece-style spans skip whitespace; boundaries come from starts and ends.
    spans = [(0, 2), (3, 5)]
    assert _boundaries(spans) == [0, 2, 3, 5]
    assert _n_split([(0, 2), (3, 5)], [2, 3]) == 0
    assert _n_continued([(0, 5)], spans) == 1


def test_renyi_uniform_is_one():
    c = Counter({i: 1 for i in range(16)})
    assert math.isclose(renyi_efficiency(c, 16), 1.0)
