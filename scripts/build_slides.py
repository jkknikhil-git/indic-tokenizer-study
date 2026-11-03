"""Phase 8: 14-slide 16:9 presentation (slides/presentation.pptx) with speaker notes.

Every number comes from results/numbers.json. Usage: python scripts/build_slides.py
"""
import json
from pathlib import Path

import qrcode
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
V = json.loads((ROOT / "results" / "numbers.json").read_text(encoding="utf-8"))["values"]
FIG = ROOT / "figures"
OUT = ROOT / "slides"
REPO = "https://github.com/jkknikhil-git/indic-tokenizer-study"

ACCENT = RGBColor(0x2A, 0x78, 0xD6)
ACCENT_SOFT = RGBColor(0xE3, 0xEE, 0xFB)
WARM = RGBColor(0xEB, 0x68, 0x34)
DARK = RGBColor(0x14, 0x16, 0x1A)
INK = RGBColor(0x1B, 0x1B, 0x1B)
MUTED = RGBColor(0x5B, 0x5B, 0x57)
LIGHT = RGBColor(0xFA, 0xFA, 0xF8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LATIN = "Segoe UI"
INDIC = "Nirmala UI"
W, H = Inches(13.333), Inches(7.5)


def v(k):
    return V[k]


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = W, H
        self.blank = self.prs.slide_layouts[6]
        self.n = 0

    def slide(self, dark=False):
        s = self.prs.slides.add_slide(self.blank)
        bg = s.background.fill
        bg.solid()
        bg.fore_color.rgb = DARK if dark else LIGHT
        self.n += 1
        if not dark:
            bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.18), H)
            bar.fill.solid()
            bar.fill.fore_color.rgb = ACCENT
            bar.line.fill.background()
            self.text(s, f"{self.n}", Inches(12.6), Inches(7.0), Inches(0.5), Inches(0.35), 11, MUTED,
                      align=PP_ALIGN.RIGHT)
        return s

    def text(self, s, text, x, y, w, h, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT, font=LATIN,
             anchor=MSO_ANCHOR.TOP):
        tb = s.shapes.add_textbox(x, y, w, h)
        tf = tb.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = Inches(0.05)
        lines = text if isinstance(text, list) else [text]
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            r = p.add_run()
            r.text = line
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.color.rgb = color
            r.font.name = font
            p.space_after = Pt(6)
        return tb

    def title(self, s, text, sub=None):
        self.text(s, text, Inches(0.55), Inches(0.35), Inches(12.2), Inches(0.8), 30, INK, bold=True)
        if sub:
            self.text(s, sub, Inches(0.55), Inches(1.05), Inches(12.2), Inches(0.5), 16, MUTED)

    def image(self, s, name, x, y, w, h):
        path = FIG / f"{name}.png" if not str(name).endswith(".png") else Path(name)
        with Image.open(path) as im:
            iw, ih = im.size
        scale = min(w / iw, h / ih)
        pw, ph = int(iw * scale), int(ih * scale)
        return s.shapes.add_picture(str(path), x + (w - pw) // 2, y + (h - ph) // 2, pw, ph)

    def tile(self, s, big, label, x, y, w=Inches(3.0), h=Inches(1.6), color=ACCENT, fill=ACCENT_SOFT):
        box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
        box.adjustments[0] = 0.08
        box.fill.solid()
        box.fill.fore_color.rgb = fill
        box.line.fill.background()
        self.text(s, big, x, y + Inches(0.12), w, Inches(0.8), 34, color, bold=True, align=PP_ALIGN.CENTER)
        self.text(s, label, x + Inches(0.1), y + Inches(0.88), w - Inches(0.2), h - Inches(0.9), 13, INK,
                  align=PP_ALIGN.CENTER)

    def box(self, s, text, x, y, w, h, fill=WHITE, line=ACCENT, size=15, color=INK, bold=False, font=LATIN):
        b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
        b.adjustments[0] = 0.12
        b.fill.solid()
        b.fill.fore_color.rgb = fill
        b.line.color.rgb = line
        b.line.width = Pt(1.5)
        tf = b.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        lines = text if isinstance(text, list) else [text]
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run()
            r.text = line
            r.font.size = Pt(size if i == 0 else size - 3)
            r.font.bold = bold if i == 0 else False
            r.font.color.rgb = color if i == 0 else MUTED
            r.font.name = font
        return b

    @staticmethod
    def notes(s, text):
        s.notes_slide.notes_text_frame.text = text

    def save(self, path):
        self.prs.save(path)


def build():
    d = Deck()

    # 1 Title
    s = d.slide(dark=True)
    d.text(s, "క్ష  ద్ర  ಕ್ಕ  स्ते  ক্ষ", Inches(0.8), Inches(0.7), Inches(11.5), Inches(1.2), 54,
           RGBColor(0x3D, 0x87, 0xE5), font=INDIC)
    d.text(s, "Measuring the Indic Tokenizer Tax", Inches(0.8), Inches(2.3), Inches(11.8), Inches(1.0), 44, WHITE,
           bold=True)
    d.text(s, "A comparative study of Sarvam AI's tokenizers and akshara-aware subword segmentation "
              "for Indian languages", Inches(0.8), Inches(3.3), Inches(11.5), Inches(1.0), 22,
           RGBColor(0xC3, 0xC2, 0xB7))
    d.text(s, ["Nikhileshwar Jakka  |  Reg. No. [REG_NO]",
               "B.Tech CSE (IoT & Intelligent Systems), Manipal University Jaipur",
               "[COURSE_CODE] Natural Language Processing  |  Guide: [FACULTY_NAME]  |  November 2026"],
           Inches(0.8), Inches(5.2), Inches(11.5), Inches(1.6), 16, RGBColor(0xC3, 0xC2, 0xB7))
    d.notes(s, "Good morning. My project measures how much more it costs, in tokens, to use large language "
               "models in Indian languages, and whether tokenizers respect the syllables our scripts are built on. "
               "The characters at the top are aksharas, conjunct syllables from Telugu, Kannada, Hindi and Bengali.")

    # 2 Hook
    s = d.slide()
    d.title(s, "The tokenizer tax", "Same FLORES sentence, translated: how many tokens compared with English?")
    d.tile(s, f"{v('parity:llama-3.1:tel_Telu')}×", "Telugu with Llama-3.1", Inches(0.7), Inches(1.9))
    d.tile(s, f"{v('parity:gpt-4o:tel_Telu')}×", "Telugu with GPT-4o", Inches(0.7), Inches(3.7), color=WARM,
           fill=RGBColor(0xFB, 0xE6, 0xDC))
    d.tile(s, f"{v('parity:sarvam-1:tel_Telu')}×", "Telugu with Sarvam-1", Inches(0.7), Inches(5.5),
           color=RGBColor(0x14, 0x8A, 0x5F), fill=RGBColor(0xDD, 0xF3, 0xEA))
    d.image(s, "fig2_parity", Inches(4.0), Inches(1.6), Inches(8.9), Inches(5.6))
    d.notes(s, f"FLORES gives us the same 1,012 sentences in every language. With Llama-3.1, a Telugu sentence costs "
               f"{v('parity:llama-3.1:tel_Telu')} times the tokens of its English translation; GPT-4o brings that to "
               f"{v('parity:gpt-4o:tel_Telu')}, Sarvam-1 to {v('parity:sarvam-1:tel_Telu')}. Because APIs bill per "
               "token and context is measured in tokens, this is a direct cost and capacity penalty.")

    # 3 Tokenizers and aksharas
    s = d.slide()
    d.title(s, "What a tokenizer does, and why aksharas matter",
            "An akshara is the written syllable of Brahmic scripts: consonants + virama + vowel sign")
    d.text(s, "Word:  क्षत्रिय  (kshatriya)", Inches(0.7), Inches(1.8), Inches(6), Inches(0.6), 24, INK, font=INDIC)
    d.text(s, "Akshara-respecting split (XLM-R, ours)", Inches(0.7), Inches(2.7), Inches(6), Inches(0.5), 16, MUTED)
    x = Inches(0.7)
    for a in ["क्ष", "त्रि", "य"]:
        d.box(s, a, x, Inches(3.2), Inches(1.4), Inches(1.0), size=30, font=INDIC)
        x += Inches(1.55)
    d.text(s, "mBERT's actual split: virama and vowel sign orphaned", Inches(0.7), Inches(4.5), Inches(6.5),
           Inches(0.5), 16, MUTED)
    x = Inches(0.7)
    for a in ["क", "्ष", "त्र", "िय"]:
        d.box(s, a, x, Inches(5.0), Inches(1.2), Inches(1.0), size=30, line=WARM, font=INDIC)
        x += Inches(1.35)
    d.box(s, ["Akshara Split Rate (ASR)", "% of aksharas that contain a token boundary"], Inches(7.6), Inches(2.0),
          Inches(5.0), Inches(1.4), fill=ACCENT_SOFT, size=20, bold=True)
    d.box(s, ["Fertility", "tokens per word"], Inches(7.6), Inches(3.6), Inches(2.4), Inches(1.3), size=18, bold=True)
    d.box(s, ["Parity", "tokens vs English"], Inches(10.2), Inches(3.6), Inches(2.4), Inches(1.3), size=18, bold=True)
    d.box(s, ["Exact byte spans", "for every token, 4 tokenizer families"], Inches(7.6), Inches(5.1), Inches(5.0),
          Inches(1.3), size=18, bold=True)
    d.notes(s, "A tokenizer cuts text into vocabulary pieces. In Brahmic scripts the natural unit is the akshara. "
               "If a boundary falls inside one, a virama or vowel sign ends up as a token on its own. I measure "
               "this with the Akshara Split Rate, alongside fertility and parity, using exact byte spans for every token.")

    # 4 Sarvam journey
    s = d.slide()
    d.title(s, "Sarvam's tokenizer journey", "Three model generations, three tokenizers")
    y = Inches(3.55)
    line = s.shapes.add_connector(1, Inches(1.0), y, Inches(12.4), y)
    line.line.color.rgb = MUTED
    line.line.width = Pt(2)
    items = [
        ("Oct 2024", "Sarvam-1", [f"{v('vocab:sarvam-1')} vocab", "custom Indic vocabulary",
                                  f"{v('vshare:pct:sarvam-1')}% Indic entries"]),
        ("May 2025", "Sarvam-M", [f"{v('vocab:sarvam-m')} vocab", "Mistral-Small-3.1 (Tekken)",
                                  f"{v('lin:sarvamm_mistral:shared_string_and_id')} entries identical"]),
        ("Mar 2026", "Sarvam-30B / 105B", [f"{v('vocab:sarvam-30b')} vocab",
                                           f"{v('lin:sarvam30b_gemma3:shared_pct')}% identical to Gemma-3",
                                           f"{v('lin:sarvam30b_gemma3:only_in_a')} slots re-assigned"]),
    ]
    for i, (date, name, facts) in enumerate(items):
        cx = Inches(1.6 + i * 4.1)
        dot = s.shapes.add_shape(MSO_SHAPE.OVAL, cx + Inches(1.35), y - Inches(0.18), Inches(0.36), Inches(0.36))
        dot.fill.solid()
        dot.fill.fore_color.rgb = ACCENT
        dot.line.fill.background()
        d.text(s, date, cx, Inches(2.3), Inches(3.1), Inches(0.5), 18, MUTED, align=PP_ALIGN.CENTER)
        d.text(s, name, cx, Inches(2.75), Inches(3.1), Inches(0.5), 22, INK, bold=True, align=PP_ALIGN.CENTER)
        d.box(s, facts, cx, Inches(4.1), Inches(3.1), Inches(1.8), size=17, bold=True)
    d.text(s, "Sources: Sarvam AI blog posts; vocabulary comparisons computed in this project.", Inches(0.6),
           Inches(6.5), Inches(12), Inches(0.4), 12, MUTED)
    d.notes(s, "Sarvam-1 had a custom 68K vocabulary. Sarvam-M was built on Mistral Small, and I verified that its "
               "vocabulary is identical to Mistral-Small-3.1. For Sarvam-30B and 105B I found that "
               f"{v('lin:sarvam30b_gemma3:shared_pct')} percent of the vocabulary is identical, same strings and same "
               f"ids, to Google's Gemma-3; {v('lin:sarvam30b_gemma3:only_in_a')} slots were re-assigned, mostly from "
               "CJK, Latin and Thai to Indic scripts.")

    # 5 Research questions
    s = d.slide()
    d.title(s, "Research questions")
    rqs = [("RQ1", "How did Sarvam's tokenizers change, and how do they compare with global tokenizers?"),
           ("RQ2", "Is there a cost gap between Indo-Aryan and Dravidian languages, or between scripts?"),
           ("RQ3", "How often do tokenizers break aksharas?"),
           ("RQ4", "Does akshara-atomic BPE remove broken aksharas without hurting fertility?")]
    for i, (k, q) in enumerate(rqs):
        x = Inches(0.7 + (i % 2) * 6.2)
        yy = Inches(1.7 + (i // 2) * 2.6)
        circ = s.shapes.add_shape(MSO_SHAPE.OVAL, x, yy + Inches(0.35), Inches(1.2), Inches(1.2))
        circ.fill.solid()
        circ.fill.fore_color.rgb = ACCENT if i < 3 else WARM
        circ.line.fill.background()
        tf = circ.text_frame
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        r = tf.paragraphs[0].add_run()
        r.text = k
        r.font.size = Pt(20)
        r.font.bold = True
        r.font.color.rgb = WHITE
        d.text(s, q, x + Inches(1.4), yy + Inches(0.3), Inches(4.5), Inches(1.6), 20, INK, anchor=MSO_ANCHOR.MIDDLE)
    d.text(s, "RQ4 is my own contribution.", Inches(0.7), Inches(6.7), Inches(8), Inches(0.4), 14, MUTED)
    d.notes(s, "Four questions: the Sarvam lineage, the language-family gap, broken aksharas, and whether my "
               "akshara-atomic BPE fixes them and at what cost.")

    # 6 Method
    s = d.slide()
    d.title(s, "Method", f"{v('n:tokenizers_published')} published + {v('n:tokenizers_ours')} trained tokenizers, "
                         f"12 languages, {v('data:flores_per_lang')} parallel sentences each")
    d.image(s, "fig0_pipeline", Inches(0.5), Inches(1.7), Inches(12.3), Inches(2.6))
    d.tile(s, v("data:train_total"), "training sentences (Sangraha)", Inches(0.7), Inches(4.7), w=Inches(3.7))
    d.tile(s, v("n:akshara_cases"), "hand-checked akshara tests, 9 scripts", Inches(4.8), Inches(4.7), w=Inches(3.7))
    d.tile(s, "1,000", "bootstrap resamples + Wilcoxon tests", Inches(8.9), Inches(4.7), w=Inches(3.7))
    d.notes(s, "Evaluation uses the parallel FLORES-200 devtest set. Each tokenizer goes through a byte-span adapter "
               "so that I know the exact bytes of every token; then the akshara segmenter and the metrics run, and "
               "finally bootstrap confidence intervals and paired Wilcoxon tests. Only tokenizer files are downloaded.")

    # 7 RQ1
    s = d.slide()
    d.title(s, "RQ1: Sarvam-30B gained on Indo-Aryan, lost on Dravidian",
            "Fertility per language with 95% bootstrap CIs")
    d.image(s, "fig3_sarvam_evolution", Inches(0.4), Inches(1.6), Inches(8.6), Inches(5.6))
    d.tile(s, v("wsv:n_b_better:fertility"), "languages better with Sarvam-30B than Sarvam-1", Inches(9.3),
           Inches(1.8), w=Inches(3.5))
    d.tile(s, v("wsv:n_b_worse:fertility"), "languages worse, incl. all 4 Dravidian", Inches(9.3), Inches(3.6),
           w=Inches(3.5), color=WARM, fill=RGBColor(0xFB, 0xE6, 0xDC))
    d.tile(s, f"{v('fertility:sarvam-m:ory_Orya')}", "Sarvam-M tokens per Odia word", Inches(9.3), Inches(5.4),
           w=Inches(3.5))
    d.notes(s, f"Against Sarvam-1, Sarvam-30B is better on {v('wsv:n_b_better:fertility')} languages such as "
               f"Bengali and Odia, but worse on {v('wsv:n_b_worse:fertility')}, including Telugu, Tamil, Kannada and "
               "Malayalam; all differences are significant after Holm correction. Sarvam-M, which kept Mistral's "
               f"vocabulary, needs {v('fertility:sarvam-m:ory_Orya')} tokens per Odia word.")

    # 8 RQ2
    s = d.slide()
    d.title(s, "RQ2: Script coverage matters more than language family", "Fertility across all tokenizers")
    d.image(s, "fig1_fertility_heatmap", Inches(0.4), Inches(1.5), Inches(8.3), Inches(5.8))
    d.tile(s, f"{v('wfam:ratio:fertility:sarvam-1')} → {v('wfam:ratio:fertility:sarvam-30b')}",
           "Dravidian / Indo-Aryan fertility, Sarvam-1 → Sarvam-30B", Inches(9.0), Inches(1.8), w=Inches(3.8))
    d.tile(s, f"{v('wfam:n_dr_higher:parity')} / {v('wfam:n_total:parity')}",
           "tokenizers where Dravidian parity is higher", Inches(9.0), Inches(3.6), w=Inches(3.8))
    d.tile(s, f"{v('parity:gpt-4o:ory_Orya')}×", "GPT-4o parity for Odia (worst language)", Inches(9.0),
           Inches(5.4), w=Inches(3.8), color=WARM, fill=RGBColor(0xFB, 0xE6, 0xDC))
    d.notes(s, "Dravidian fertility is higher for almost every tokenizer, partly because agglutinative words are "
               "longer. Parity controls for content: Dravidian text costs more in only "
               f"{v('wfam:n_dr_higher:parity')} tokenizers, mostly byte-level ones. The bigger driver is script "
               "coverage: Odia is the most expensive language for GPT-4o and Sarvam-M.")

    # 9 Token visualisation
    s = d.slide()
    d.title(s, "What the tokenizers actually see", "Red bars = token boundary inside an akshara; grey hex = byte fragments")
    d.image(s, "fig7_token_visualisation", Inches(0.4), Inches(1.5), Inches(12.5), Inches(5.9))
    d.notes(s, "The same Hindi and Telugu sentence under five tokenizers. Llama-3.1 falls back to raw UTF-8 bytes "
               "for Telugu, shown as hex boxes. Sarvam and GPT-4o leave vowel signs as separate tokens. My "
               "akshara-atomic tokenizer never splits an akshara here.")

    # 10 RQ3
    s = d.slide()
    d.title(s, "RQ3: Byte-level tokenizers break almost every akshara", "Akshara Split Rate by tokenizer")
    d.image(s, "fig4_asr", Inches(0.4), Inches(1.5), Inches(8.6), Inches(5.6))
    d.tile(s, f"{v('asr:llama-3.1:indic')}%", "aksharas split by Llama-3.1", Inches(9.3), Inches(1.8), w=Inches(3.5),
           color=WARM, fill=RGBColor(0xFB, 0xE6, 0xDC))
    d.tile(s, f"{v('asr:sarvam-30b:indic')}%", "aksharas split by Sarvam-30B", Inches(9.3), Inches(3.6), w=Inches(3.5))
    d.tile(s, f"{v('wfam:ratio:asr:sarvam-30b')}×", "Sarvam-30B: Dravidian vs Indo-Aryan split rate",
           Inches(9.3), Inches(5.4), w=Inches(3.5))
    d.notes(s, f"GPT-4's cl100k splits {v('asr:gpt-4:indic')} percent of aksharas and Llama-3.1 "
               f"{v('asr:llama-3.1:indic')} percent. Indic-aware tokenizers do much better, but Sarvam-30B splits "
               f"Dravidian aksharas {v('wfam:ratio:asr:sarvam-30b')} times as often as Indo-Aryan ones.")

    # 11 RQ4
    s = d.slide()
    d.title(s, "RQ4: Akshara-atomic BPE", "Each frequent akshara gets one private-use symbol before BPE training")
    d.image(s, "fig6_ours_vs_vocab", Inches(0.4), Inches(1.6), Inches(8.7), Inches(4.2))
    d.tile(s, f"{v('asr:ours-bpe-64k:indic')}% → {v('asr:ours-akshara-bpe-64k:indic')}%",
           "Akshara Split Rate at 64K", Inches(9.3), Inches(1.8), w=Inches(3.6))
    d.tile(s, f"+{v('rq4:fert_increase_pct:64k')}%", "fertility cost at 64K", Inches(9.3), Inches(3.6), w=Inches(3.6),
           color=WARM, fill=RGBColor(0xFB, 0xE6, 0xDC))
    d.tile(s, v("cov:split_mapped:ours-akshara-bpe-64k"), "mapped aksharas ever split", Inches(9.3), Inches(5.4),
           w=Inches(3.6))
    d.text(s, f"Every remaining split is on one of the {v('cov:oov_pct:ours-akshara-bpe-64k')}% of aksharas outside "
              f"the mapped inventory. vs Sarvam-1: fertility {v('fertility:ours-akshara-bpe-64k:indic')} vs "
              f"{v('fertility:sarvam-1:indic')}, ASR {v('rq4:asr_ratio_sarvam1_over_ours64k')}× lower.",
           Inches(0.6), Inches(6.0), Inches(8.5), Inches(1.0), 15, MUTED)
    d.notes(s, f"At 64K, akshara-atomic BPE cuts the split rate from {v('asr:ours-bpe-64k:indic')} to "
               f"{v('asr:ours-akshara-bpe-64k:indic')} percent, while fertility rises by "
               f"{v('rq4:fert_increase_pct:64k')} percent. The cost shrinks as the vocabulary grows. "
               "The remaining splits all come from rare aksharas outside the mapped inventory. About "
               f"{v('bare:extra_share_pct:64k')} percent of the extra tokens are standalone word-boundary tokens, "
               "which suggests an easy improvement.")

    # 12 Takeaways
    s = d.slide()
    d.title(s, "Key takeaways")
    take = [
        (f"{v('lin:sarvam30b_gemma3:shared_pct')}%", "of Sarvam-30B's vocabulary is identical to Gemma-3"),
        (f"{v('wsv:n_b_worse:fertility')} / 11", "languages got more expensive from Sarvam-1 to Sarvam-30B"),
        (f"{v('parity:llama-3.1:tel_Telu')}×", "Telugu token premium on Llama-3.1"),
        (f"−{v('rq4:asr_reduction_pct:64k')}%", "akshara splits with akshara-atomic BPE (64K)"),
    ]
    for i, (big, lab) in enumerate(take):
        d.tile(s, big, lab, Inches(0.7 + (i % 2) * 6.2), Inches(1.7 + (i // 2) * 2.6), w=Inches(5.8), h=Inches(2.2),
               color=ACCENT if i != 2 else WARM, fill=ACCENT_SOFT if i != 2 else RGBColor(0xFB, 0xE6, 0xDC))
    d.notes(s, "Four things to remember: the Sarvam-30B tokenizer is mostly Gemma-3; it made Dravidian languages more "
               "expensive than Sarvam-1; byte-level global tokenizers charge Indian users many times more; and "
               "akshara-atomic BPE removes almost all akshara splits for a small fertility cost.")

    # 13 Limitations and future work
    s = d.slide()
    d.title(s, "Limitations and future work")
    lim = ["Whitespace words penalise agglutinative languages", "FLORES is a single (Wikipedia-style) domain",
           "Intrinsic metrics only: no models trained", "Akshara rules approximate syllables"]
    fut = ["Train small LMs per tokenizer to test downstream effects", "Add IN22 and conversational text",
           "Combine akshara units with morphology-aware segmentation", "Cover all 22 scheduled languages"]
    d.text(s, "Limitations", Inches(0.7), Inches(1.5), Inches(5.8), Inches(0.5), 22, WARM, bold=True)
    d.text(s, "Future work", Inches(6.9), Inches(1.5), Inches(5.8), Inches(0.5), 22, ACCENT, bold=True)
    for i, (a, b) in enumerate(zip(lim, fut)):
        d.box(s, a, Inches(0.7), Inches(2.2 + i * 1.2), Inches(5.8), Inches(1.0), line=WARM, size=16)
        d.box(s, b, Inches(6.9), Inches(2.2 + i * 1.2), Inches(5.8), Inches(1.0), size=16)
    d.notes(s, "The main limitations: fertility depends on a whitespace word definition, FLORES is one domain, and "
               "everything is intrinsic. Next I want to train small models on each tokenizer to see whether fewer "
               "broken aksharas actually improve downstream quality.")

    # 14 Thank you
    s = d.slide(dark=True)
    d.text(s, "Thank you", Inches(0.8), Inches(1.5), Inches(7.5), Inches(1.2), 54, WHITE, bold=True)
    d.text(s, "Questions?", Inches(0.8), Inches(2.7), Inches(7.5), Inches(0.8), 28, RGBColor(0xC3, 0xC2, 0xB7))
    d.text(s, ["Code, data pointers, results, paper and slides:", REPO], Inches(0.8), Inches(4.3), Inches(7.8),
           Inches(1.2), 18, RGBColor(0x3D, 0x87, 0xE5))
    d.text(s, "Nikhileshwar Jakka  |  jkk.nikhil@gmail.com", Inches(0.8), Inches(5.7), Inches(7.5), Inches(0.5), 16,
           RGBColor(0xC3, 0xC2, 0xB7))
    qr_path = OUT / "repo_qr.png"
    qrcode.make(REPO, border=2).save(qr_path)
    s.shapes.add_picture(str(qr_path), Inches(9.1), Inches(1.6), Inches(3.4), Inches(3.4))
    d.text(s, "Scan for the repository", Inches(9.1), Inches(5.1), Inches(3.4), Inches(0.5), 14,
           RGBColor(0xC3, 0xC2, 0xB7), align=PP_ALIGN.CENTER)
    d.notes(s, "Thank you. Everything is reproducible with one command from the repository linked here. "
               "I'm happy to take questions.")
    return d


def main():
    OUT.mkdir(exist_ok=True)
    d = build()
    d.save(OUT / "presentation.pptx")
    print("wrote", OUT / "presentation.pptx", "slides:", d.n)


if __name__ == "__main__":
    main()
