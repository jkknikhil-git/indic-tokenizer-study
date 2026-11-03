"""Build paper/main.pdf with tectonic and package paper/overleaf.zip.

Usage: python scripts/build_paper.py [--tectonic PATH]
"""
import argparse
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper"
FIGS_USED = ["fig1_fertility_heatmap", "fig3_sarvam_evolution", "fig4_asr", "fig6_ours_vs_vocab",
             "fig7_token_visualisation"]
FONTS_USED = ["NotoSansDevanagari", "NotoSansTelugu", "NotoSansTamil", "NotoSansKannada", "NotoSansMalayalam"]


def find_tectonic(arg):
    for cand in (arg, shutil.which("tectonic"), r"D:\DevTools\tectonic\tectonic.exe"):
        if cand and Path(cand).exists():
            return cand
    raise SystemExit("tectonic not found: install it or pass --tectonic")


def stage():
    figs, fonts = PAPER / "figs", PAPER / "fonts"
    figs.mkdir(exist_ok=True)
    fonts.mkdir(exist_ok=True)
    for f in FIGS_USED:
        shutil.copy2(ROOT / "figures" / f"{f}.pdf", figs / f"{f}.pdf")
    for f in FONTS_USED:
        shutil.copy2(ROOT / "fonts" / f"{f}-Regular.ttf", fonts / f"{f}-Regular.ttf")


def overleaf_zip():
    out = PAPER / "overleaf.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in ["main.tex", "anthology.bib", "extra.bib", "README_overleaf.txt"]:
            z.write(PAPER / rel, rel)
        for sub in ("generated", "figs", "fonts"):
            for f in sorted((PAPER / sub).iterdir()):
                z.write(f, f"{sub}/{f.name}")
    print("wrote", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tectonic")
    args = ap.parse_args()
    stage()
    env = dict(os.environ)
    env.setdefault("TECTONIC_CACHE_DIR", str(ROOT / ".cache" / "tectonic"))
    subprocess.run([find_tectonic(args.tectonic), "-X", "compile", "--keep-logs", "main.tex"],
                   cwd=PAPER, check=True, env=env)
    overleaf_zip()


if __name__ == "__main__":
    main()
