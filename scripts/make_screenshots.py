"""Run each result command and save its real terminal output as a PNG in screenshots/.

The images are rendered from the captured stdout of the commands below (nothing is typed by hand).
Usage: python scripts/make_screenshots.py
"""
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "screenshots"
PY = sys.executable
SHOTS = [
    ("01_tests", "python -m pytest -q", [PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"]),
    ("02_final_check", "python scripts/final_check.py", [PY, "scripts/final_check.py"]),
    ("03_key_results", "python scripts/show_results.py summary", [PY, "scripts/show_results.py", "summary"]),
    ("04_vocab_lineage", "python scripts/show_results.py lineage", [PY, "scripts/show_results.py", "lineage"]),
    ("05_sarvam1_vs_sarvam30b", "python scripts/show_results.py sarvam", [PY, "scripts/show_results.py", "sarvam"]),
    ("06_indo_aryan_vs_dravidian", "python scripts/show_results.py family", [PY, "scripts/show_results.py", "family"]),
    ("07_our_tokenizers", "python scripts/show_results.py ours", [PY, "scripts/show_results.py", "ours"]),
]
BG, FG, PROMPT, CMD = (12, 12, 12), (204, 204, 204), (110, 200, 120), (240, 240, 240)
FONT_PATH = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "consola.ttf"


def render(name: str, shown_cmd: str, text: str):
    font = ImageFont.truetype(str(FONT_PATH), 17) if FONT_PATH.exists() else ImageFont.load_default()
    lines = text.rstrip("\n").splitlines()
    prompt = r"PS D:\PROJECTS\indic-tokenizer-study> "
    all_lines = [prompt + shown_cmd] + lines
    cw = font.getbbox("M")[2]
    lh = 22
    width = max(len(line) for line in all_lines) * cw + 40
    height = (len(all_lines) + 1) * lh + 50
    img = Image.new("RGB", (max(width, 900), height), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width, 28], fill=(36, 36, 36))
    d.text((12, 5), f"captured output: {shown_cmd}", font=font, fill=(200, 200, 200))
    y = 40
    d.text((16, y), prompt, font=font, fill=PROMPT)
    d.text((16 + len(prompt) * cw, y), shown_cmd, font=font, fill=CMD)
    for line in lines:
        y += lh
        d.text((16, y), line, font=font, fill=FG)
    img.save(OUT / f"{name}.png")


def main():
    OUT.mkdir(exist_ok=True)
    env = dict(os.environ, PYTHONUTF8="1", PYTHONWARNINGS="ignore")
    for name, shown, cmd in SHOTS:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env)
        out = r.stdout if r.stdout.strip() else r.stderr
        render(name, shown, out)
        print(f"saved screenshots/{name}.png (exit {r.returncode})")


if __name__ == "__main__":
    main()
