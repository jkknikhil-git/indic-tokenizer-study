"""Download FLORES-200 (official tarball) and the Noto Sans fonts used by the figures."""
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from config import FLORES_DIR, FONTS, RAW  # noqa: E402
from data import FLORES_URL  # noqa: E402

FONT_URL = "https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/{f}/hinted/ttf/{f}-{w}.ttf"
FONT_FAMILIES = ["NotoSans", "NotoSansDevanagari", "NotoSansBengali", "NotoSansGujarati", "NotoSansGurmukhi",
                 "NotoSansOriya", "NotoSansTelugu", "NotoSansTamil", "NotoSansKannada", "NotoSansMalayalam"]


def main():
    if not FLORES_DIR.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        tgz = RAW / "flores200_dataset.tar.gz"
        print("downloading", FLORES_URL)
        urllib.request.urlretrieve(FLORES_URL, tgz)
        with tarfile.open(tgz) as tf:
            tf.extractall(RAW / "flores", filter="data")
    FONTS.mkdir(exist_ok=True)
    for f in FONT_FAMILIES:
        for w in ("Regular", "Bold"):
            out = FONTS / f"{f}-{w}.ttf"
            if not out.exists():
                urllib.request.urlretrieve(FONT_URL.format(f=f, w=w), out)
    print("assets ready")


if __name__ == "__main__":
    main()
