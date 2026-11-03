"""decode(encode(x)) == x for our trained tokenizers on 1,000 held-out sentences."""
import pytest

from config import CORPUS_DIR, LANGS
from train_tokenizers import LocalSPTokenizer, local_entries


def heldout(n=1000):
    sents = []
    for lang in LANGS:
        path = CORPUS_DIR / f"heldout_{lang}.txt"
        if path.exists():
            sents += [s for s in path.read_text(encoding="utf-8").splitlines() if s]
    return sents[:n]


ENTRIES = local_entries()
HELDOUT = heldout()


@pytest.mark.skipif(not ENTRIES or len(HELDOUT) < 1000, reason="trained models / held-out corpus not present")
@pytest.mark.parametrize("entry", ENTRIES, ids=[e.key for e in ENTRIES])
def test_roundtrip(entry):
    tok = LocalSPTokenizer(entry)
    bad = [s for s in HELDOUT if tok.roundtrip(s) != s]
    assert not bad, f"{len(bad)} sentences failed, e.g. {bad[0]!r}"
    # byte spans must also reconstruct the input exactly
    for s in HELDOUT[:200]:
        enc = tok.encode(s)
        b = s.encode("utf-8")
        assert enc.spans is not None and b"".join(b[x:y] for x, y in enc.spans) == b
        assert all(enc.spans[i][1] == enc.spans[i + 1][0] for i in range(len(enc.spans) - 1))


@pytest.mark.skipif(not ENTRIES, reason="trained models not present")
def test_akshara_atomic_never_splits_mapped_aksharas():
    from akshara import akshara_spans
    for entry in [e for e in ENTRIES if "akshara" in e.key]:
        tok = LocalSPTokenizer(entry)
        for s in HELDOUT[:300]:
            enc = tok.encode(s)
            starts = {a for a, _ in enc.spans}
            offs = [len(s[:i].encode("utf-8")) for i in range(len(s) + 1)]
            for a, b in akshara_spans(s):
                if s[a:b] in tok.mapper.fwd:
                    assert not any(offs[a] < x < offs[b] for x in starts)
