"""Hand-checked akshara segmentations, at least one conjunct case per script."""
import pytest

from akshara import SCRIPT_RULES, ScriptRule, akshara_byte_spans, aksharas

CASES = [
    # Devanagari (Hindi / Marathi)
    ("क्षत्रिय", ["क्ष", "त्रि", "य"]),
    ("हिन्दी", ["हि", "न्दी"]),
    ("नमस्ते", ["न", "म", "स्ते"]),
    ("महाराष्ट्र", ["म", "हा", "रा", "ष्ट्र"]),
    ("क्‌ष", ["क्‌ष"]),  # explicit halant (ZWNJ) still one akshara
    ("जगत् में", ["ज", "ग", "त्", " ", "में"]),  # word-final virama does not cross a space
    # Bengali / Assamese
    ("বাংলা", ["বাং", "লা"]),
    ("ক্ষমা", ["ক্ষ", "মা"]),
    ("স্ত্রী", ["স্ত্রী"]),
    ("অসমীয়া", ["অ", "স", "মী", "য়া"]),
    # Gurmukhi
    ("ਪੰਜਾਬੀ", ["ਪੰ", "ਜਾ", "ਬੀ"]),
    ("ਪ੍ਰੀਤ", ["ਪ੍ਰੀ", "ਤ"]),
    # Gujarati
    ("ગુજરાતી", ["ગુ", "જ", "રા", "તી"]),
    ("ક્ષમા", ["ક્ષ", "મા"]),
    # Odia
    ("ଓଡ଼ିଆ", ["ଓ", "ଡ଼ି", "ଆ"]),
    ("ସ୍କୁଲ", ["ସ୍କୁ", "ଲ"]),
    # Telugu
    ("తెలుగు", ["తె", "లు", "గు"]),
    ("ద్రావిడ", ["ద్రా", "వి", "డ"]),
    ("స్త్రీ", ["స్త్రీ"]),
    # Tamil: pulli does not join by default
    ("தமிழ்", ["த", "மி", "ழ்"]),
    ("பக்கம்", ["ப", "க்", "க", "ம்"]),
    ("க்ஷ", ["க்ஷ"]),
    # Kannada
    ("ಕನ್ನಡ", ["ಕ", "ನ್ನ", "ಡ"]),
    ("ಅಕ್ಕ", ["ಅ", "ಕ್ಕ"]),
    # Malayalam
    ("മലയാളം", ["മ", "ല", "യാ", "ളം"]),
    ("ക്ഷമ", ["ക്ഷ", "മ"]),
    ("അവൻ", ["അ", "വ", "ൻ"]),  # atomic chillu
    ("എന്‍റെ", ["എ", "ന്‍", "റെ"]),  # legacy chillu (virama+ZWJ) is standalone
    ("സ്ത്രീ", ["സ്ത്രീ"]),
    # Latin passes through as grapheme clusters
    ("ab", ["a", "b"]),
]


@pytest.mark.parametrize("text,expected", CASES)
def test_segmentation(text, expected):
    assert aksharas(text) == expected


@pytest.mark.parametrize("text,_", CASES)
def test_spans_cover_text(text, _):
    assert "".join(aksharas(text)) == text


def test_tamil_joining_is_configurable():
    rules = dict(SCRIPT_RULES)
    rules["Tamil"] = ScriptRule(join_virama=True)
    assert aksharas("பக்கம்", rules) == ["ப", "க்க", "ம்"]


def test_byte_spans_indic_only():
    text = "a हिन्दी"
    spans = akshara_byte_spans(text)
    b = text.encode("utf-8")
    assert [b[s:e].decode() for s, e in spans] == ["हि", "न्दी"]
