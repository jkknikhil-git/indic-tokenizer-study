"""Shared paths, language table and constants for the study."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
FLORES_DIR = RAW / "flores" / "flores200_dataset"
CORPUS_DIR = DATA / "corpus"
MODELS_DIR = ROOT / "models"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
FONTS = ROOT / "fonts"
CACHE = ROOT / ".cache"

# Keep Hugging Face downloads inside the project (C: on the dev laptop is nearly full).
os.environ.setdefault("HF_HOME", str(CACHE / "hf"))
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

SEED = 13
CONTEXT_WINDOW = 8192

# flores code -> metadata. "family" drives the Indo-Aryan vs Dravidian comparisons.
LANGS = {
    "eng_Latn": dict(name="English", family="Reference", script="Latin", sangraha="eng", wiki="en"),
    "hin_Deva": dict(name="Hindi", family="Indo-Aryan", script="Devanagari", sangraha="hin", wiki="hi"),
    "mar_Deva": dict(name="Marathi", family="Indo-Aryan", script="Devanagari", sangraha="mar", wiki="mr"),
    "ben_Beng": dict(name="Bengali", family="Indo-Aryan", script="Bengali", sangraha="ben", wiki="bn"),
    "asm_Beng": dict(name="Assamese", family="Indo-Aryan", script="Bengali", sangraha="asm", wiki="as"),
    "guj_Gujr": dict(name="Gujarati", family="Indo-Aryan", script="Gujarati", sangraha="guj", wiki="gu"),
    "pan_Guru": dict(name="Punjabi", family="Indo-Aryan", script="Gurmukhi", sangraha="pan", wiki="pa"),
    "ory_Orya": dict(name="Odia", family="Indo-Aryan", script="Oriya", sangraha="ori", wiki="or"),
    "tel_Telu": dict(name="Telugu", family="Dravidian", script="Telugu", sangraha="tel", wiki="te"),
    "tam_Taml": dict(name="Tamil", family="Dravidian", script="Tamil", sangraha="tam", wiki="ta"),
    "kan_Knda": dict(name="Kannada", family="Dravidian", script="Kannada", sangraha="kan", wiki="kn"),
    "mal_Mlym": dict(name="Malayalam", family="Dravidian", script="Malayalam", sangraha="mal", wiki="ml"),
}
INDIC = [k for k, v in LANGS.items() if v["family"] != "Reference"]
INDO_ARYAN = [k for k, v in LANGS.items() if v["family"] == "Indo-Aryan"]
DRAVIDIAN = [k for k, v in LANGS.items() if v["family"] == "Dravidian"]

# Unicode blocks of the Brahmic scripts used here: script -> (start, end) inclusive.
SCRIPT_BLOCKS = {
    "Devanagari": (0x0900, 0x097F),
    "Bengali": (0x0980, 0x09FF),
    "Gurmukhi": (0x0A00, 0x0A7F),
    "Gujarati": (0x0A80, 0x0AFF),
    "Oriya": (0x0B00, 0x0B7F),
    "Tamil": (0x0B80, 0x0BFF),
    "Telugu": (0x0C00, 0x0C7F),
    "Kannada": (0x0C80, 0x0CFF),
    "Malayalam": (0x0D00, 0x0D7F),
}

for _d in (RESULTS, FIGURES, CORPUS_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
