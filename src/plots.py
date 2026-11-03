"""Phase 5: all figures (300 dpi PNG + PDF) from the CSVs in results/.

Usage: python src/plots.py
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

from akshara import akshara_byte_spans  # noqa: E402
from config import DRAVIDIAN, FIGURES, FONTS, INDO_ARYAN, LANGS, RESULTS  # noqa: E402

# Validated categorical palette (dataviz reference instance, light mode), fixed order.
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#ffffff"
FAMILY_COLOR = {"Indo-Aryan": C[0], "Dravidian": C[1]}
GROUP_COLOR = {"Sarvam": C[0], "Proprietary": C[1], "Open LLM": C[2], "Encoder": C[6], "Ours": C[7]}
SCRIPT_FONTS = ["Devanagari", "Bengali", "Gujarati", "Gurmukhi", "Oriya", "Telugu", "Tamil", "Kannada", "Malayalam"]

ZOO_ORDER = ["sarvam-1", "sarvam-m", "sarvam-30b", "gpt-4o", "gpt-4", "llama-3.1", "gemma-3", "qwen-2.5",
             "muril", "indicbert-v2", "xlm-r", "mbert"]
OURS_MAIN = ["ours-bpe-64k", "ours-akshara-bpe-64k", "ours-unigram-64k"]
LANG_ORDER = ["eng_Latn"] + INDO_ARYAN + DRAVIDIAN


def setup_fonts():
    for f in sorted(FONTS.glob("*.ttf")):
        fm.fontManager.addfont(str(f))
    families = ["Noto Sans"] + [f"Noto Sans {s}" for s in SCRIPT_FONTS]
    plt.rcParams.update({
        "font.family": families, "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK,
        "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": False, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.dpi": 300,
        "legend.frameon": False, "axes.titleweight": "bold", "axes.titlesize": 10, "pdf.fonttype": 42,
    })


def save(fig, name: str):
    for ext in ("png", "pdf"):
        fig.savefig(FIGURES / f"{name}.{ext}", bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print("saved", name)


def ygrid(ax):
    ax.yaxis.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def load():
    s = pd.read_csv(RESULTS / "benchmark_summary.csv")
    info = pd.read_csv(RESULTS / "tokenizer_info.csv").set_index("tokenizer")
    return s, info


def lang_label(l):
    return LANGS[l]["name"]


def present(keys, s):
    have = set(s.tokenizer)
    return [k for k in keys if k in have]


# 1 -----------------------------------------------------------------------------------
def fig_fertility_heatmap(s, info):
    keys = present(ZOO_ORDER + OURS_MAIN, s)
    piv = s.pivot(index="tokenizer", columns="lang", values="fertility").loc[keys, LANG_ORDER]
    unk = s.pivot(index="tokenizer", columns="lang", values="unk_rate").loc[keys, LANG_ORDER]
    labels = [info.loc[k, "label"] for k in keys]
    fig, ax = plt.subplots(figsize=(8.2, 0.34 * len(keys) + 1.4))
    data = np.log10(piv.to_numpy())
    im = ax.imshow(data, cmap="Blues", aspect="auto", vmin=0, vmax=np.log10(20))
    for i in range(len(keys)):
        for j in range(len(LANG_ORDER)):
            v = piv.iat[i, j]
            flag = "†" if unk.iat[i, j] > 5 else ""
            ax.text(j, i, f"{v:.2f}{flag}", ha="center", va="center", fontsize=7,
                    color="white" if data[i, j] > 0.75 else INK)
    ax.set_xticks(range(len(LANG_ORDER)), [lang_label(l) for l in LANG_ORDER], rotation=40, ha="right")
    ax.set_yticks(range(len(keys)), labels)
    for x in (0.5, 0.5 + len(INDO_ARYAN)):
        ax.axvline(x, color="white", lw=3)
    for y, k in enumerate(keys):
        if k.startswith("ours") and (y == 0 or not keys[y - 1].startswith("ours")):
            ax.axhline(y - 0.5, color="white", lw=3)
    top = ax.secondary_xaxis("top")
    top.set_xticks([0, 1 + (len(INDO_ARYAN) - 1) / 2, 1 + len(INDO_ARYAN) + (len(DRAVIDIAN) - 1) / 2],
                   ["Ref.", "Indo-Aryan", "Dravidian"])
    top.tick_params(length=0)
    top.spines["top"].set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    ticks = [1, 2, 5, 10, 20]
    cb.set_ticks(np.log10(ticks), labels=[str(t) for t in ticks])
    cb.set_label("Fertility (tokens / word, log scale)")
    cb.outline.set_visible(False)
    ax.set_title("Fertility on FLORES-200 devtest", loc="left", pad=22)
    if (unk > 5).any().any():
        ax.text(0, -0.13, "† more than 5% of tokens are [UNK]; the low value reflects unknown words, "
                "not efficient coverage.", transform=ax.transAxes, fontsize=7, color=INK2, va="top")
    save(fig, "fig1_fertility_heatmap")


# 2 -----------------------------------------------------------------------------------
def fig_parity(s, info):
    keys = present(ZOO_ORDER + OURS_MAIN, s)
    keys = sorted(keys, key=lambda k: s[(s.tokenizer == k) & s.lang.isin(INDO_ARYAN + DRAVIDIAN)].parity.mean())
    fig, ax = plt.subplots(figsize=(7.2, 0.36 * len(keys) + 1.0))
    h = 0.38
    for i, k in enumerate(keys):
        for off, fam, langs in ((-h / 2, "Indo-Aryan", INDO_ARYAN), (h / 2, "Dravidian", DRAVIDIAN)):
            vals = s[(s.tokenizer == k) & s.lang.isin(langs)].parity
            ax.barh(i + off, vals.mean(), height=h - 0.04, color=FAMILY_COLOR[fam],
                    label=fam if i == 0 else None)
            ax.scatter(vals, np.full(len(vals), i + off), s=9, color=INK, zorder=3, lw=0,
                       label="single language" if (i == 0 and fam == "Indo-Aryan") else None)
    ax.axvline(1.0, color=INK, lw=1, ls="--")
    ax.text(1.02, len(keys) - 0.4, "parity with English = 1.0", fontsize=7, color=INK2, va="bottom")
    ax.set_yticks(range(len(keys)), [info.loc[k, "label"] for k in keys])
    ax.set_xlabel("Parity = tokens(language) / tokens(English) on the same FLORES sentences")
    ax.xaxis.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title("Tokenizer premium relative to English (bars: family mean, dots: languages)", loc="left")
    save(fig, "fig2_parity")


# 3 -----------------------------------------------------------------------------------
def fig_sarvam_evolution(s, info):
    keys = present(["sarvam-1", "sarvam-m", "sarvam-30b"], s)
    langs = LANG_ORDER
    x = np.arange(len(langs))
    w = 0.8 / len(keys)
    fig, ax = plt.subplots(figsize=(8, 3.3))
    for i, k in enumerate(keys):
        piv = s[s.tokenizer == k].set_index("lang").loc[langs]
        xs = x + (i - (len(keys) - 1) / 2) * w
        ax.bar(xs, piv.fertility, width=w - 0.03, color=C[i],
               label=f"{info.loc[k, 'label']} ({info.loc[k, 'vocab_size']:,} vocab)")
        if "fertility_lo" in piv:
            ax.errorbar(xs, piv.fertility, yerr=[piv.fertility - piv.fertility_lo, piv.fertility_hi - piv.fertility],
                        fmt="none", ecolor=INK, lw=0.6, capsize=1.5)
    ax.set_xticks(x, [lang_label(l) for l in langs], rotation=35, ha="right")
    ax.set_ylabel("Fertility (tokens / word)")
    ygrid(ax)
    ax.axvline(0.5, color=GRID, lw=1)
    ax.axvline(0.5 + len(INDO_ARYAN), color=GRID, lw=1)
    ymax = ax.get_ylim()[1]
    for xx, t in ((0, "Ref."), (1 + (len(INDO_ARYAN) - 1) / 2, "Indo-Aryan"),
                  (1 + len(INDO_ARYAN) + (len(DRAVIDIAN) - 1) / 2, "Dravidian")):
        ax.text(xx, ymax * 0.98, t, ha="center", va="top", fontsize=8, color=INK2)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.32), ncol=3, fontsize=8)
    ax.set_title("Sarvam tokenizer lineage: fertility per language (95% bootstrap CI)", loc="left")
    save(fig, "fig3_sarvam_evolution")


# 4 -----------------------------------------------------------------------------------
def fig_asr(s, info):
    keys = present(ZOO_ORDER + OURS_MAIN, s)
    rows = []
    for k in keys:
        for fam, langs in (("Indo-Aryan", INDO_ARYAN), ("Dravidian", DRAVIDIAN)):
            v = s[(s.tokenizer == k) & s.lang.isin(langs)].asr.mean()
            rows.append((k, fam, v))
    df = pd.DataFrame(rows, columns=["tokenizer", "family", "asr"])
    order = df.groupby("tokenizer").asr.mean().sort_values().index.tolist()
    x = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(8, 3.4))
    for i, fam in enumerate(("Indo-Aryan", "Dravidian")):
        v = df[df.family == fam].set_index("tokenizer").loc[order].asr
        b = ax.bar(x + (i - 0.5) * 0.4, v, width=0.38, color=FAMILY_COLOR[fam], label=fam)
        for rect, val in zip(b, v):
            ax.text(rect.get_x() + rect.get_width() / 2, val + 1, f"{val:.0f}" if val >= 1 else f"{val:.1f}",
                    ha="center", va="bottom", fontsize=6, color=INK2)
    ax.set_xticks(x, [info.loc[k, "label"] for k in order], rotation=40, ha="right")
    ax.set_ylabel("Akshara Split Rate (%)")
    ax.set_ylim(0, 108)
    ygrid(ax)
    ax.legend(loc="upper left")
    ax.set_title("Share of aksharas containing an internal token boundary (mean over languages)", loc="left")
    save(fig, "fig4_asr")


# 5 -----------------------------------------------------------------------------------
def fig_vocab(info):
    v = pd.read_csv(RESULTS / "vocab_composition.csv")
    keys = [k for k in ZOO_ORDER + OURS_MAIN if k in set(v.tokenizer)]
    brahmic = SCRIPT_FONTS
    piv = v.pivot_table(index="tokenizer", columns="script", values="pct", aggfunc="sum").fillna(0).loc[keys]
    coarse = pd.DataFrame(index=keys)
    coarse["Indic (9 Brahmic scripts)"] = piv[[c for c in brahmic if c in piv]].sum(axis=1)
    coarse["Latin"] = piv.get("Latin", 0)
    coarse["CJK"] = piv.get("CJK", 0)
    other_scripts = [c for c in piv.columns if c not in brahmic + ["Latin", "CJK", "Digits/Symbols",
                                                                     "Partial byte sequence", "Special", "Whitespace", "Mixed"]]
    coarse["Other scripts"] = piv[other_scripts].sum(axis=1)
    coarse["Digits, symbols, mixed, special"] = piv[[c for c in ("Digits/Symbols", "Special", "Whitespace", "Mixed")
                                                     if c in piv]].sum(axis=1)
    coarse["Partial UTF-8 bytes"] = piv.get("Partial byte sequence", 0)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 0.33 * len(keys) + 1.6), sharey=True,
                                 gridspec_kw=dict(width_ratios=[1, 1.15], wspace=0.08))
    y = np.arange(len(keys))
    left = np.zeros(len(keys))
    # Indic in the accent colour; everything else in neutral greys so panel (a) never reuses (b)'s hues.
    cols = ["#2a78d6", "#6f6e69", "#9c9b95", "#c4c3bd", "#e4e3df", "#3d3c39"]
    for col, color in zip(coarse.columns, cols):
        a1.barh(y, coarse[col], left=left, color=color, label=col, height=0.72, edgecolor=SURFACE, lw=0.8)
        left += coarse[col].to_numpy()
    a1.set_xlim(0, 100)
    a1.set_xlabel("% of vocabulary")
    a1.set_yticks(y, [info.loc[k, "label"] for k in keys])
    a1.invert_yaxis()
    a1.legend(loc="upper left", bbox_to_anchor=(0, -0.12), ncol=2, fontsize=7)
    a1.set_title("(a) Vocabulary by script", loc="left")
    # (b) absolute number of tokens per Brahmic script
    counts = v.pivot_table(index="tokenizer", columns="script", values="n_tokens", aggfunc="sum").fillna(0).loc[keys]
    left = np.zeros(len(keys))
    pal = C + ["#7f7f7f"]
    for col, color in zip(brahmic, pal):
        vals = counts[col].to_numpy() / 1000 if col in counts else np.zeros(len(keys))
        a2.barh(y, vals, left=left, color=color, label=col, height=0.72, edgecolor=SURFACE, lw=0.6)
        left += vals
    a2.set_xlabel("Indic vocabulary entries (thousands)")
    a2.legend(loc="upper left", bbox_to_anchor=(0, -0.12), ncol=5, fontsize=7)
    a2.set_title("(b) Indic entries per script", loc="left")
    a2.xaxis.grid(True, color=GRID, lw=0.6)
    a2.set_axisbelow(True)
    save(fig, "fig5_vocab_composition")


# 6 -----------------------------------------------------------------------------------
def fig_ours(s, info):
    indic = INDO_ARYAN + DRAVIDIAN
    ours = s[s.tokenizer.str.startswith("ours")].copy()
    if ours.empty:
        return
    ours["size"] = ours.tokenizer.str.extract(r"-(\d+)k$").astype(float) * 1000
    ours["kind"] = np.where(ours.tokenizer.str.contains("akshara"), "Akshara-atomic BPE",
                            np.where(ours.tokenizer.str.contains("unigram"), "Unigram", "Standard BPE"))
    agg = ours[ours.lang.isin(indic)].groupby(["kind", "size"])[["fertility", "asr"]].mean().reset_index()
    refs = [(k, info.loc[k, "vocab_size"]) for k in ("sarvam-1", "sarvam-30b") if k in info.index]
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.2))
    for ax, metric, ylabel in ((axes[0], "fertility", "Mean fertility (11 Indic languages)"),
                               (axes[1], "asr", "Mean Akshara Split Rate (%)")):
        for kind, color, marker in (("Standard BPE", C[0], "o"), ("Akshara-atomic BPE", C[1], "s"),
                                    ("Unigram", C[2], "D")):
            d = agg[agg.kind == kind].sort_values("size")
            if d.empty:
                continue
            ax.plot(d["size"], d[metric], color=color, marker=marker, lw=2, ms=6, label=kind)
            last = d.iloc[-1]
            dy = {"Standard BPE": 5, "Akshara-atomic BPE": 0, "Unigram": -6}[kind] if metric == "fertility" else 0
            ax.annotate(f"{last[metric]:.2f}", (last["size"], last[metric]), xytext=(7, dy),
                        textcoords="offset points", fontsize=7, color=INK2, va="center")
        for k, vs in refs:
            val = s[(s.tokenizer == k) & s.lang.isin(indic)][metric].mean()
            ax.scatter([vs], [val], marker="*", s=110, color=GROUP_COLOR["Sarvam"] if k == "sarvam-1" else C[6],
                       zorder=4, label=info.loc[k, "label"], edgecolor=SURFACE, lw=0.8)
            ax.annotate(f"{val:.2f}", (vs, val), xytext=(6, 0), textcoords="offset points", fontsize=7,
                        color=INK2, va="center")
        ax.set_xscale("log", base=2)
        ticks = [16000, 32000, 64000, 128000, 262144]
        ax.set_xticks(ticks, ["16K", "32K", "64K", "128K", "262K"])
        ax.minorticks_off()
        ax.set_xlabel("Vocabulary size (log scale)")
        ax.set_ylabel(ylabel)
        ygrid(ax)
    axes[0].set_title("(a) Fertility vs vocabulary size", loc="left")
    axes[1].set_title("(b) Akshara splits vs vocabulary size", loc="left")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.08), fontsize=8)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save(fig, "fig6_ours_vs_vocab")


# 7 -----------------------------------------------------------------------------------
VIZ_TOKENIZERS = ["gpt-4o", "llama-3.1", "sarvam-1", "sarvam-30b", "ours-akshara-bpe-64k"]


def pick_sentence(max_words=(5, 8)) -> int:
    from data import load_flores
    fl = load_flores("devtest", ["eng_Latn", "hin_Deva", "tel_Telu"])
    best = None
    for sid in range(len(fl["eng_Latn"])):
        n_h, n_t = len(fl["hin_Deva"][sid].split()), len(fl["tel_Telu"][sid].split())
        if max_words[0] <= n_t <= max_words[1] and n_h <= 12 and "‌" not in fl["tel_Telu"][sid]:
            score = len(fl["hin_Deva"][sid]) + len(fl["tel_Telu"][sid])
            if best is None or score < best[0]:
                best = (score, sid)
    return best[1]


def _display(piece: bytes) -> tuple[str, bool]:
    try:
        return piece.decode("utf-8").replace(" ", "·"), True
    except UnicodeDecodeError:
        return " ".join(f"{b:02X}" for b in piece), False


def fig_token_viz(info):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from data import load_flores
    from tokenizers_zoo import ZOO, load as load_tok
    from train_tokenizers import local_entries
    entries = {e.key: e for e in list(ZOO) + local_entries()}
    keys = [k for k in VIZ_TOKENIZERS if k in entries and k in info.index]
    sid = pick_sentence()
    fl = load_flores("devtest", ["hin_Deva", "tel_Telu"])
    toks = {k: load_tok(entries[k]) for k in keys}
    width = 15.0
    fig = plt.figure(figsize=(width, 7.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width)
    ax.set_ylim(0, 7.4)
    ax.axis("off")
    renderer = fig.canvas.get_renderer()
    y = 7.1
    fills = ["#dbe8f8", "#fbe1d6"]
    for lang in ("hin_Deva", "tel_Telu"):
        sent = fl[lang][sid]
        ax.text(0.15, y, f"{LANGS[lang]['name']} (FLORES devtest #{sid}): {sent}", fontsize=11, color=INK,
                va="center", fontweight="bold")
        y -= 0.42
        for k in keys:
            enc = toks[k].encode(sent)
            ref = enc.ref_text.encode("utf-8")
            aks = akshara_byte_spans(enc.ref_text)
            n_split = sum(1 for a, b in aks if any(a < s0 < b for s0, _ in enc.spans))
            label = f"{info.loc[k, 'label']}\n{enc.n_tokens} tokens, {n_split}/{len(aks)} aksharas split"
            ax.text(0.15, y, label, fontsize=8.5, color=INK, va="center")
            x = 2.75
            for j, (s0, e0) in enumerate(enc.spans):
                txt, ok = _display(ref[s0:e0])
                broken = any(a < s0 < b for a, b in aks)
                t = ax.text(x + 0.05, y, txt, fontsize=12 if ok else 6.5, va="center", ha="left", color=INK,
                            family=None if ok else "monospace", zorder=3)
                bb = t.get_window_extent(renderer).transformed(ax.transData.inverted())
                w = bb.width + 0.1
                if x + w > width - 0.1:
                    y -= 0.42
                    x = 2.75
                    t.set_position((x + 0.05, y))
                ax.add_patch(FancyBboxPatch((x, y - 0.16), w, 0.32, boxstyle="round,pad=0,rounding_size=0.04",
                                            fc=fills[j % 2] if ok else "#ececec", ec="#9a9994", lw=0.5, zorder=2))
                if broken:
                    ax.plot([x, x], [y - 0.2, y + 0.2], color=C[7], lw=2.2, zorder=4)
                x += w + 0.03
            y -= 0.5
        y -= 0.12
    ax.text(0.15, 0.18, "Boxes = tokens (alternating colours). Grey boxes with hex = byte fragments that are not "
            "a complete character. Red bar = token boundary inside an akshara. · = space.",
            fontsize=8.5, color=INK2)
    fig.set_size_inches(width, 7.4)
    save(fig, "fig7_token_visualisation")
    return sid


# 8 -----------------------------------------------------------------------------------
def fig_context(s, info):
    keys = present(["gpt-4o", "llama-3.1", "sarvam-1", "sarvam-30b", "ours-akshara-bpe-64k"], s)
    langs = LANG_ORDER
    x = np.arange(len(langs))
    w = 0.8 / len(keys)
    fig, ax = plt.subplots(figsize=(8.4, 3.4))
    for i, k in enumerate(keys):
        v = s[s.tokenizer == k].set_index("lang").loc[langs].words_in_8k
        ax.bar(x + (i - (len(keys) - 1) / 2) * w, v, width=w - 0.02, color=C[i], label=info.loc[k, "label"])
    ax.set_xticks(x, [lang_label(l) for l in langs], rotation=35, ha="right")
    ax.set_ylabel("Words that fit in 8,192 tokens")
    ygrid(ax)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.3), ncol=5, fontsize=8)
    ax.set_title("Effective context: how much text an 8K-token window holds", loc="left")
    save(fig, "fig8_effective_context")


def fig_pipeline():
    """Method pipeline diagram (used by the report and slides)."""
    steps = [("FLORES-200 devtest\n12 languages x 1,012\nparallel sentences", C[0]),
             ("Tokenizer zoo\n12 published tokenizers\n+ 7 trained here", C[2]),
             ("Byte-span adapters\ntiktoken / byte-level /\nSentencePiece / WordPiece", C[6]),
             ("Akshara segmenter\ngrapheme clusters +\nvirama joining", C[1]),
             ("Metrics\nfertility, parity, ASR,\nPCW, effective context", C[3]),
             ("Statistics\nbootstrap CIs,\nWilcoxon tests", C[7])]
    fig, ax = plt.subplots(figsize=(11, 2.1))
    ax.set_xlim(0, len(steps) * 1.9)
    ax.set_ylim(0, 2)
    ax.axis("off")
    for i, (txt, col) in enumerate(steps):
        x0 = i * 1.9 + 0.05
        ax.add_patch(FancyBboxPatch((x0, 0.35), 1.6, 1.3, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    fc="white", ec=col, lw=2))
        ax.text(x0 + 0.8, 1.0, txt, ha="center", va="center", fontsize=8.5, color=INK)
        if i < len(steps) - 1:
            ax.annotate("", xy=(x0 + 1.86, 1.0), xytext=(x0 + 1.66, 1.0),
                        arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.2))
    ax.text(0.05, 0.08, "Training branch (RQ4): Sangraha 600K sentences -> akshara mapping to Private Use Area "
            "-> SentencePiece BPE -> inverse mapping", fontsize=8, color=INK2)
    save(fig, "fig0_pipeline")


def main():
    setup_fonts()
    s, info = load()
    fig_pipeline()
    fig_fertility_heatmap(s, info)
    fig_parity(s, info)
    fig_sarvam_evolution(s, info)
    fig_asr(s, info)
    fig_vocab(info)
    fig_ours(s, info)
    sid = fig_token_viz(info)
    fig_context(s, info)
    (RESULTS / "figure_meta.json").write_text(json.dumps({"token_viz_sentence_id": sid}), encoding="utf-8")


if __name__ == "__main__":
    main()
