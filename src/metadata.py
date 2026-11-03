"""Write results/run_metadata.json: versions, seeds, data sources, tokenizer revisions,
and the mirror-vs-official checks for Llama-3.1 and Gemma-3.

Usage: python src/metadata.py
"""
from __future__ import annotations

import base64
import importlib.metadata as md
import json
import platform
import sys
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from config import CACHE, CORPUS_DIR, FLORES_DIR, LANGS, RAW, RESULTS, SEED

PKGS = ["transformers", "tokenizers", "sentencepiece", "tiktoken", "datasets", "huggingface_hub", "regex",
        "pandas", "numpy", "scipy", "matplotlib", "seaborn", "pyarrow", "python-docx", "python-pptx", "Pillow"]
LLAMA_OFFICIAL_URL = "https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3/tokenizer.model"


def hf_revisions() -> dict:
    out = {}
    hub = CACHE / "hf" / "hub"
    for d in sorted(hub.glob("models--*")):
        repo = d.name[len("models--"):].replace("--", "/")
        ref = d / "refs" / "main"
        out[repo] = ref.read_text().strip() if ref.exists() else None
    return out


def _tree_oids(repo: str) -> dict:
    url = f"https://huggingface.co/api/models/{repo}/tree/main"
    with urllib.request.urlopen(url, timeout=30) as r:
        return {x["path"]: x.get("oid") for x in json.load(r)}


def verify_mirrors() -> dict:
    from tokenizers_zoo import ZOO, load
    res = {}
    # Gemma-3: compare git blob ids of the tokenizer files (listing of the gated repo is public).
    try:
        off, mir = _tree_oids("google/gemma-3-1b-it"), _tree_oids("unsloth/gemma-3-1b-it")
        res["gemma-3"] = {f: dict(official=off.get(f), mirror=mir.get(f), identical=off.get(f) == mir.get(f))
                          for f in ("tokenizer.json", "tokenizer.model")}
    except Exception as ex:  # noqa: BLE001
        res["gemma-3"] = f"check failed: {ex}"
    # Llama-3.1: Meta's tiktoken BPE file from the public llama-models GitHub repo.
    try:
        path = RAW / "llama_official" / "tokenizer.model"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(LLAMA_OFFICIAL_URL, path)
        official = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            t, r = line.split()
            official[base64.b64decode(t)] = int(r)
        tok = load(next(e for e in ZOO if e.key == "llama-3.1"))
        mirror = {tok._piece_bytes(t): i for t, i in tok.vocab.items() if t not in tok.added}
        res["llama-3.1"] = dict(official_source=LLAMA_OFFICIAL_URL, official_base_tokens=len(official),
                                mirror_base_tokens=len(mirror), mirror_special_tokens=len(tok.added),
                                identical_token_to_id_map=official == mirror)
    except Exception as ex:  # noqa: BLE001
        res["llama-3.1"] = f"check failed: {ex}"
    return res


def main():
    versions = {}
    for p in PKGS:
        try:
            versions[p] = md.version(p)
        except md.PackageNotFoundError:
            versions[p] = None
    corpus = json.loads((RESULTS / "corpus_stats.json").read_text(encoding="utf-8"))
    flores_counts = {l: len((FLORES_DIR / "devtest" / f"{l}.devtest").read_text(encoding="utf-8").splitlines())
                     for l in LANGS}
    info = pd.read_csv(RESULTS / "tokenizer_info.csv")
    meta = dict(
        generated_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        python=sys.version.split()[0], platform=platform.platform(), processor=platform.processor(),
        seed=SEED, library_versions=versions,
        evaluation=dict(dataset="FLORES-200 devtest", source="https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz",
                        sentences_per_language=flores_counts),
        second_benchmark=dict(dataset="ai4bharat/IN22-Gen", status="skipped: gated on the Hugging Face Hub (needs login)"),
        training_corpus=dict(source="ai4bharat/sangraha, verified split, shards data-0/data-1 (streamed)",
                             per_language={x["lang"]: dict(train=x["train_sentences"], heldout=x["heldout_sentences"],
                                                           docs_read=x["docs"], eval_overlap_removed=x["eval_overlap"],
                                                           duplicates_removed=x["duplicates"], source=x.get("source"))
                                           for x in corpus["languages"]},
                             overlap_rule=corpus["overlap_rule"],
                             local_files=sorted(p.name for p in CORPUS_DIR.glob("*.txt"))),
        tokenizers=info.to_dict(orient="records"),
        hf_revisions=hf_revisions(),
        mirror_verification=verify_mirrors(),
    )
    training_log = RESULTS / "training_log.json"
    if training_log.exists():
        meta["own_tokenizer_training"] = json.loads(training_log.read_text(encoding="utf-8"))
    (RESULTS / "run_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote run_metadata.json")


if __name__ == "__main__":
    main()
