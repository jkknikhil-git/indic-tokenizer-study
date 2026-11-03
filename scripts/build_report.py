"""Phase 7: university project report (report/report.docx) generated with python-docx.

Every number comes from results/numbers.json (written by src/report_numbers.py).
Usage: python scripts/build_report.py
"""
import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from config import DRAVIDIAN, INDIC, INDO_ARYAN, LANGS  # noqa: E402

V = json.loads((ROOT / "results" / "numbers.json").read_text(encoding="utf-8"))["values"]
FIG = ROOT / "figures"
REPO = "https://github.com/jkknikhil-git/indic-tokenizer-study"
TITLE = ("Measuring the Indic Tokenizer Tax: A Comparative Study of Sarvam AI's Tokenizers and "
         "Akshara-Aware Subword Segmentation for Indian Languages")
FONT = "Times New Roman"


def v(key):
    return V[key]


# ---------------------------------------------------------------- docx helpers
def set_cell_font(cell, size=9, bold=False):
    for p in cell.paragraphs:
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for r in p.runs:
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.name = FONT


def add_field(paragraph, instr, placeholder=""):
    """Insert a Word field (e.g. 'TOC \\o "1-3" \\h', 'SEQ Figure \\* ARABIC')."""
    r = paragraph.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "begin")
    r._r.append(fld)
    r2 = paragraph.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f" {instr} "
    r2._r.append(it)
    r3 = paragraph.add_run()
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    r3._r.append(sep)
    paragraph.add_run(placeholder)
    r5 = paragraph.add_run()
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    r5._r.append(end)


class Report:
    def __init__(self):
        self.doc = Document()
        self.fig_n = 0
        self.tab_n = 0
        self.chapter = 0
        self._styles()

    def _styles(self):
        d = self.doc
        sec = d.sections[0]
        for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
            setattr(sec, side, Inches(1))
        st = d.styles["Normal"]
        st.font.name = FONT
        st.font.size = Pt(12)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        pf = st.paragraph_format
        pf.line_spacing = 1.5
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.space_after = Pt(6)
        for name, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 12), ("Title", 20)):
            h = d.styles[name]
            h.font.name = FONT
            h.font.size = Pt(size)
            h.font.bold = True
            h.font.color.rgb = RGBColor(0, 0, 0)
            rpr = h.element.get_or_add_rPr()
            rfonts = rpr.find(qn("w:rFonts"))
            if rfonts is None:
                rfonts = OxmlElement("w:rFonts")
                rpr.append(rfonts)
            for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                rfonts.set(qn(a), FONT)
            h.paragraph_format.space_before = Pt(12)
            h.paragraph_format.space_after = Pt(6)
            h.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        cap = d.styles["Caption"]
        cap.font.name = FONT
        cap.font.size = Pt(10)
        cap.font.italic = False
        cap.font.bold = False
        cap.font.color.rgb = RGBColor(0, 0, 0)
        cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        # page numbers in the footer
        p = sec.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_field(p, "PAGE", "1")

    # -- text
    def para(self, text, bold=False, italic=False, align=None, size=None, space_after=None):
        p = self.doc.add_paragraph()
        self._runs(p, text, bold, italic, size)
        if align is not None:
            p.alignment = align
        if space_after is not None:
            p.paragraph_format.space_after = Pt(space_after)
        return p

    @staticmethod
    def _runs(p, text, bold=False, italic=False, size=None):
        # **bold** segments inside text
        parts = text.split("**")
        for i, part in enumerate(parts):
            if not part:
                continue
            r = p.add_run(part)
            r.bold = bold or (i % 2 == 1)
            r.italic = italic
            if size:
                r.font.size = Pt(size)

    def bullets(self, items):
        for it in items:
            p = self.doc.add_paragraph(style="List Bullet")
            self._runs(p, it)
            p.paragraph_format.line_spacing = 1.5

    def numbered(self, items):
        for it in items:
            p = self.doc.add_paragraph(style="List Number")
            self._runs(p, it)

    def heading_chapter(self, title):
        self.chapter += 1
        self.section = 0
        self.page_break()
        self.doc.add_heading(f"Chapter {self.chapter}: {title}", level=1)

    def heading_section(self, title):
        self.section += 1
        self.doc.add_heading(f"{self.chapter}.{self.section} {title}", level=2)

    def heading_plain(self, title, level=1, toc=True):
        h = self.doc.add_heading(title, level=level)
        if not toc:
            h.style = self.doc.styles["Title"]
        return h

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def figure(self, name, caption, width=6.2):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.0
        p.add_run().add_picture(str(FIG / f"{name}.png"), width=Inches(width))
        self.fig_n += 1
        c = self.doc.add_paragraph(style="Caption")
        c.add_run("Figure ")
        add_field(c, "SEQ Figure \\* ARABIC", str(self.fig_n))
        c.add_run(f": {caption}")

    def table(self, header, rows, caption, widths=None, size=9):
        self.tab_n += 1
        c = self.doc.add_paragraph(style="Caption")
        c.add_run("Table ")
        add_field(c, "SEQ Table \\* ARABIC", str(self.tab_n))
        c.add_run(f": {caption}")
        t = self.doc.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, h in enumerate(header):
            t.rows[0].cells[i].text = h
            set_cell_font(t.rows[0].cells[i], size, bold=True)
        for row in rows:
            cells = t.add_row().cells
            for i, val in enumerate(row):
                cells[i].text = str(val)
                set_cell_font(cells[i], size)
        if widths:
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Inches(w)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)
        return t

    def code(self, text):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.left_indent = Inches(0.3)
        r = p.add_run(text)
        r.font.name = "Consolas"
        r.font.size = Pt(9)

    def save(self, path):
        self.doc.save(path)


# ---------------------------------------------------------------- content
def front_matter(R: Report):
    d = R.doc
    first = len(d.paragraphs)
    R.para("MANIPAL UNIVERSITY JAIPUR", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=16)
    R.para("Department of Computer Science and Engineering", align=WD_ALIGN_PARAGRAPH.CENTER, size=13)
    d.add_paragraph()
    R.para("A Project Report on", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    R.para(TITLE, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=17)
    d.add_paragraph()
    R.para("Submitted in partial fulfilment of the requirements of the course", align=WD_ALIGN_PARAGRAPH.CENTER)
    R.para("Natural Language Processing (NLP)", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    d.add_paragraph()
    R.para("Submitted by", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    R.para("Nikhileshwar Jakka", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=14)
    R.para("Reg. No. 23FE10CII00213", align=WD_ALIGN_PARAGRAPH.CENTER)
    R.para("B.Tech CSE (IoT & Intelligent Systems)", align=WD_ALIGN_PARAGRAPH.CENTER)
    d.add_paragraph()
    R.para("Under the guidance of", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    R.para("Heena Kalim", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    R.para("Department of Computer Science and Engineering", align=WD_ALIGN_PARAGRAPH.CENTER)
    d.add_paragraph()
    R.para("Manipal University Jaipur, Jaipur, Rajasthan, India", align=WD_ALIGN_PARAGRAPH.CENTER)
    R.para("November 2026", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    for p in d.paragraphs[first:]:  # the cover uses tighter spacing so it fits on one page
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(4)

    R.page_break()
    R.heading_plain("Certificate", toc=False).alignment = WD_ALIGN_PARAGRAPH.CENTER
    R.para(f"This is to certify that the project report entitled “{TITLE}”, submitted by "
           "Nikhileshwar Jakka (Reg. No. 23FE10CII00213) in partial fulfilment of the requirements of the course "
           "Natural Language Processing (NLP), is a bonafide record of the work carried out by the "
           "student under my supervision during the academic year 2026–27.")
    for _ in range(3):
        R.doc.add_paragraph()
    R.para("Heena Kalim\nDepartment of Computer Science and Engineering\n"
           "Manipal University Jaipur", align=WD_ALIGN_PARAGRAPH.LEFT)
    R.para("Date: ____________          Signature: ____________", align=WD_ALIGN_PARAGRAPH.LEFT)

    R.page_break()
    R.heading_plain("Declaration", toc=False).alignment = WD_ALIGN_PARAGRAPH.CENTER
    R.para(f"I, Nikhileshwar Jakka (Reg. No. 23FE10CII00213), hereby declare that the project report entitled "
           f"“{TITLE}” is my own work, carried out under the guidance of Heena Kalim. All results "
           "reported here were produced by code that I ran and that is publicly available. All sources have "
           "been acknowledged and cited. This work has not been submitted elsewhere for any other degree or course.")
    for _ in range(3):
        R.doc.add_paragraph()
    R.para("Nikhileshwar Jakka\nReg. No. 23FE10CII00213\nPlace: Jaipur          Date: ____________",
           align=WD_ALIGN_PARAGRAPH.LEFT)

    R.page_break()
    R.heading_plain("Acknowledgement", toc=False).alignment = WD_ALIGN_PARAGRAPH.CENTER
    R.para("I thank my guide, Heena Kalim, for advice and feedback throughout this project, and the "
           "Department of Computer Science and Engineering, Manipal University Jaipur, for the course that "
           "motivated it. I also thank the teams who released the open resources this study relies on: "
           "Meta AI for FLORES-200, AI4Bharat for Sangraha, IndicBERTv2 and IndicTrans2, Sarvam AI, Google, "
           "Meta, Alibaba Qwen, Mistral AI and OpenAI for public tokenizers, and the maintainers of SentencePiece, "
           "Hugging Face Tokenizers and the Noto fonts.")

    R.page_break()
    R.heading_plain("Abstract", toc=False).alignment = WD_ALIGN_PARAGRAPH.CENTER
    R.para(
        "Large language models read text through a tokenizer, and the same content can need many more tokens in "
        "an Indian language than in English. That raises the cost of every API call, shrinks the usable context "
        "and slows generation. This project measures this “tokenizer tax” for 11 Indian languages "
        f"on the parallel FLORES-200 devtest set across {v('n:tokenizers_published')} published tokenizers, with a "
        "focus on the three generations of Sarvam AI models. Exact UTF-8 byte spans are recovered for every "
        "token, which lets us measure how often tokenizers break aksharas, the orthographic syllables of Brahmic "
        f"scripts. Sarvam-M turns out to reuse the Mistral-Small-3.1 vocabulary unchanged "
        f"({v('lin:sarvamm_mistral:shared_string_and_id')} identical entries), and Sarvam-30B/105B shares "
        f"{v('lin:sarvam30b_gemma3:shared_pct')}% of its vocabulary, with identical ids, with Gemma-3. Compared "
        f"with Sarvam-1, Sarvam-30B lowers fertility on {v('wsv:n_b_better:fertility')} Indo-Aryan languages but "
        "raises it on all four Dravidian languages, widening the Dravidian/Indo-Aryan fertility ratio from "
        f"{v('wfam:ratio:fertility:sarvam-1')} to {v('wfam:ratio:fertility:sarvam-30b')}. Byte-level tokenizers "
        f"such as Llama-3.1 split {v('asr:llama-3.1:indic')}% of aksharas. Finally, the project proposes "
        "akshara-atomic BPE, which gives every frequent akshara its own base symbol. At a 64K vocabulary it "
        f"cuts the Akshara Split Rate from {v('asr:ours-bpe-64k:indic')}% to "
        f"{v('asr:ours-akshara-bpe-64k:indic')}% for a {v('rq4:fert_increase_pct:64k')}% increase in fertility.")
    R.para("**Keywords:** tokenization, Indian languages, byte-pair encoding, fertility, akshara, Sarvam AI")

    R.page_break()
    R.heading_plain("Table of Contents", toc=False)
    add_field(R.doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u', "Right-click and choose Update Field.")
    R.page_break()
    R.heading_plain("List of Figures", toc=False)
    add_field(R.doc.add_paragraph(), 'TOC \\h \\z \\c "Figure"', "Right-click and choose Update Field.")
    R.heading_plain("List of Tables", toc=False)
    add_field(R.doc.add_paragraph(), 'TOC \\h \\z \\c "Table"', "Right-click and choose Update Field.")


def chapter1(R):
    R.heading_chapter("Introduction")
    R.heading_section("Background")
    R.para("A tokenizer turns text into the integer ids a language model consumes. Modern LLMs use subword "
           "tokenizers such as byte-pair encoding (BPE) and Unigram, learned mostly from English-heavy data. "
           "When a vocabulary has few entries for a script, text in that script breaks into many short pieces, "
           f"sometimes single bytes. On FLORES-200, GPT-4o’s o200k tokenizer needs {v('parity:gpt-4o:tel_Telu')}× "
           f"as many tokens for Telugu as for the same content in English, and Llama-3.1 needs "
           f"{v('parity:llama-3.1:tel_Telu')}×. Because APIs charge per token and context windows are counted in "
           "tokens, this premium falls directly on Indian users.")
    R.para("Indian scripts are abugidas. The natural writing unit is the akshara, an orthographic syllable built "
           "from consonants, viramas (vowel killers) and dependent vowel signs. A boundary inside an akshara "
           "leaves a vowel sign or virama as a token on its own, which no reader would treat as a unit.")
    R.heading_section("Problem statement")
    R.para("Sarvam AI, a Bengaluru company, has released three generations of models with three different "
           "tokenizers: Sarvam-1 (October 2024), Sarvam-M (May 2025) and the open-weight Sarvam-30B and "
           "Sarvam-105B (March 2026). There is no independent, reproducible measurement of how these tokenizers "
           "differ, how they compare with global tokenizers, whether Dravidian languages pay more than Indo-Aryan "
           "ones, or how often aksharas are broken.")
    R.heading_section("Objectives")
    R.numbered([
        "**RQ1.** Trace how Sarvam’s tokenizers changed across generations and compare them with general multilingual tokenizers.",
        "**RQ2.** Test for a systematic cost gap between Indo-Aryan and Dravidian languages, and between scripts.",
        "**RQ3.** Measure how often tokenizers break aksharas.",
        "**RQ4.** Design akshara-atomic BPE and measure its effect on akshara splits and fertility across vocabulary sizes.",
    ])
    R.heading_section("Scope")
    R.para("The study covers English and 11 Indian languages in 9 Brahmic scripts: seven Indo-Aryan (Hindi, "
           "Marathi, Bengali, Assamese, Gujarati, Punjabi, Odia) and four Dravidian (Telugu, Tamil, Kannada, "
           "Malayalam). All metrics are intrinsic and were computed on a CPU laptop. No language model was trained, "
           "and only tokenizer files were downloaded.")


def chapter2(R):
    R.heading_chapter("Literature Review")
    R.para("Sennrich et al. introduced BPE for neural machine translation [1]. Kudo proposed the Unigram language "
           "model tokenizer with subword regularisation [2], and SentencePiece made both language-independent by "
           "operating on raw text [3]. Byte-level BPE (tiktoken [4], Llama 3 [5]) works on UTF-8 bytes, so it never "
           "produces unknown tokens but can split a character into fragments.")
    R.para("Rust et al. defined fertility and the proportion of continued words and showed that a poor tokenizer "
           "hurts monolingual performance of multilingual models [6]. Petrov et al. introduced tokenization parity "
           "on parallel text and found premiums of up to 15× [7]. Ahia et al. quantified how this "
           "becomes a cost disparity in commercial APIs [8]. Zouhar et al. related tokenization quality to Rényi "
           "entropy [9].")
    R.para("For Indian languages, IndicNLPSuite [10], IndicBERTv2 with IndicXTREME [11] and MuRIL [12] built "
           "Indic encoders with large Indic vocabularies; IndicTrans2 released the IN22 benchmark [13]; Sangraha, "
           "part of IndicLLMSuite, provides verified pre-training text [14]; FLORES-200 provides professionally "
           "translated parallel sentences [15], [16]. Recent work focuses on Indic tokenizers directly: Brahma et al. "
           "evaluate BPE and Unigram on 17 Indian languages [17], MorphTok adds morphology-aware pre-tokenization and "
           "a constrained BPE that keeps dependent vowel signs attached [18], and Rana et al. design a multilingual "
           "tokenizer with an Indic variant [19]. Sarvam AI documents its models in official blog posts [20]–[22].")
    R.table(["Work", "Year", "Focus", "Relevance here"], [
        ["Sennrich et al. [1]", "2016", "BPE subwords for NMT", "Base algorithm for most tokenizers studied"],
        ["Kudo; Kudo & Richardson [2], [3]", "2018", "Unigram LM, SentencePiece", "Training toolkit for our models"],
        ["Rust et al. [6]", "2021", "Fertility, continued words", "Core metrics"],
        ["Petrov et al. [7]", "2023", "Parity across languages", "Parity metric, fairness framing"],
        ["Ahia et al. [8]", "2023", "API cost disparity", "Cost multiplier interpretation"],
        ["Zouhar et al. [9]", "2023", "Rényi efficiency", "Additional intrinsic metric"],
        ["Doddapaneni et al. [11]", "2023", "IndicBERTv2, IndicXTREME", "Indic encoder baseline"],
        ["Khanuja et al. [12]", "2021", "MuRIL", "Indic encoder baseline"],
        ["Khan et al. [14]", "2024", "Sangraha corpus", "Training data for our tokenizers"],
        ["Brahma et al. [17]", "2025", "Indic tokenizer evaluation", "Closest evaluation study"],
        ["Brahma et al. (MorphTok) [18]", "2025", "Constrained BPE for abugidas", "Closest method to akshara-atomic BPE"],
    ], "Summary of prior work", widths=[1.9, 0.5, 1.8, 2.3])
    R.para("The gap this project fills is a reproducible, statistically tested comparison of the Sarvam tokenizer "
           "lineage, an exact byte-level measurement of akshara splits for every tokenizer family, and an "
           "akshara-atomic BPE that removes such splits by construction.")


def chapter3(R):
    R.heading_chapter("Methodology and System Design")
    R.figure("fig0_pipeline", "Method pipeline: evaluation branch (top) and training branch (bottom).", 6.4)
    R.heading_section("Data")
    R.para(f"Evaluation uses FLORES-200 devtest, {v('data:flores_per_lang')} parallel sentences per language, "
           "from the official tarball. The IN22-Gen benchmark is gated on the Hugging Face Hub and was skipped. "
           f"For training, {v('data:train_per_lang')} sentences per language ({v('data:train_total')} in total, plus "
           f"{v('data:heldout_total')} held out) were streamed from the verified split of Sangraha, deduplicated, "
           "and filtered so that no sentence shares a normalised 40-character substring with FLORES dev or devtest "
           f"({v('data:overlap_removed')} sentences matched).")
    R.heading_section("Tokenizer zoo")
    info = __import__("pandas").read_csv(ROOT / "results" / "tokenizer_info.csv")
    rows = [[r.label, r.source, r.family, f"{int(r.vocab_size):,}", r.span_mode] for r in info.itertuples()]
    R.table(["Tokenizer", "Source", "Algorithm", "Vocab", "Spans"], rows, "Tokenizers evaluated",
            widths=[1.4, 2.1, 1.7, 0.7, 0.6], size=8)
    R.para("Llama-3.1 and Gemma-3 were loaded from public mirrors. The Llama-3.1 mirror’s "
           f"{v('mirror:llama_base_tokens')} token-to-id pairs match Meta’s official llama-models file exactly, "
           "and the Gemma-3 mirror’s files have the same git blob hashes as Google’s repository. Sarvam-30B "
           "and Sarvam-105B have byte-identical vocabularies and merges, so they are reported as one row.")
    R.heading_section("Metrics")
    R.para("Words are obtained by whitespace splitting with punctuation removed, using one rule for every tokenizer.")
    R.bullets([
        "**Fertility** = total tokens / total words.",
        "**Parity** = tokens for the language / tokens for the parallel English sentences (the API cost multiplier).",
        "**Akshara Split Rate (ASR)** = % of aksharas that contain an internal token boundary.",
        "**Intra-character split rate** = % of codepoints whose UTF-8 bytes are split across tokens.",
        "**Proportion of continued words (PCW)**, **words per 8,192 tokens**, **[UNK] rate** and **Rényi efficiency** (α = 2.5).",
    ])
    R.para("Uncertainty is reported as 95% bootstrap confidence intervals (1,000 resamples of sentences). "
           "Comparisons use paired Wilcoxon signed-rank tests over FLORES sentences with Holm correction, and the "
           "rank-biserial correlation r as effect size.")
    R.heading_section("Akshara-atomic BPE")
    R.para("Every Indic akshara in the training corpus is counted. The most frequent min(n₂, V/2) types, where "
           f"n₂ = {v('inv:types_ge2')} types occur at least twice, are mapped to codepoints in the Supplementary "
           "Private Use Area-A (U+F0000 onwards). SentencePiece BPE is trained on the mapped text, and the "
           "encode/decode wrappers apply and reverse the mapping. Merges can combine aksharas but can never "
           "split a mapped one.")


def chapter4(R):
    R.heading_chapter("Implementation")
    R.heading_section("Tools and environment")
    R.para("Python 3.11 in a virtual environment on a Windows 11 laptop (Intel Core i5-11320H, 16 GB RAM, no GPU). "
           "Libraries: Hugging Face transformers and tokenizers, tiktoken, SentencePiece, regex, pandas, SciPy, "
           "matplotlib, python-docx and python-pptx. The paper was typeset with tectonic (XeLaTeX). Exact versions "
           "are logged in results/run_metadata.json.")
    R.heading_section("Repository structure")
    R.table(["Path", "Purpose"], [
        ["src/data.py", "FLORES loader; Sangraha streaming, filtering, deduplication, overlap removal"],
        ["src/tokenizers_zoo.py", "Common interface and byte-span adapters for all tokenizer families"],
        ["src/akshara.py", "Akshara segmenter with per-script rules"],
        ["src/metrics.py", "Sentence-level and aggregated metrics"],
        ["src/stats.py", "Bootstrap CIs, Wilcoxon tests, Holm correction"],
        ["src/vocab_analysis.py", "Vocabulary script composition and lineage comparison"],
        ["src/train_tokenizers.py", "Standard, akshara-atomic and Unigram tokenizers"],
        ["src/plots.py", "All figures (300 dpi PNG + PDF)"],
        ["src/report_numbers.py", "Every number quoted in paper, report and slides"],
        ["tests/", "Akshara, metric and round-trip tests (pytest)"],
    ], "Repository map", widths=[2.0, 4.4])
    R.heading_section("Key algorithms")
    R.para("Akshara joining: after grapheme clustering, a cluster that ends in a virama joins the next one when that "
           "cluster starts with a consonant of the same script (Tamil and Malayalam chillu rules aside):")
    R.code("for cl, start, end in _base_clusters(text):\n"
           "    if prev and is_consonant(cl[0]) and script_of(cl[0]) == prev.script \\\n"
           "            and prev.rule.join_virama:\n"
           "        out[-1][1] = end          # extend the previous akshara\n"
           "    else:\n"
           "        out.append([start, end])\n"
           "    prev = dead_consonant(cl)   # ends in virama (+ZWJ/ZWNJ)?")
    R.para("Byte spans for byte-level BPE map each token back through the GPT-2 byte-to-unicode table, then assert "
           "that the pieces reconstruct the input exactly:")
    R.code("pieces = [bytes(BYTE_DECODER[c] for c in tok) for tok in enc.tokens]\n"
           "assert b''.join(pieces) == normalised_text.encode('utf-8')")
    R.para("The akshara mapping replaces each mapped akshara with one private-use codepoint before SentencePiece sees it:")
    R.code("def map(self, text):\n"
           "    return ''.join(self.fwd.get(text[s:e], text[s:e]) for s, e in akshara_spans(text))")
    R.heading_section("Verification")
    R.para(f"The test suite covers {v('n:akshara_cases')} hand-checked akshara segmentations across all nine scripts, "
           "the metric helpers, and a round-trip test showing decode(encode(x)) = x on 1,000 held-out sentences for "
           "all seven trained tokenizers. Span validation succeeded for at least "
           f"{v('span:min_ok')} of {v('span:total')} sentences for every published tokenizer.")


def chapter5(R):
    R.heading_chapter("Results and Discussion")
    R.heading_section("Overall picture")
    R.figure("fig1_fertility_heatmap", "Fertility on FLORES-200 devtest for every tokenizer and language "
             "(† marks more than 5% [UNK] tokens).", 6.3)
    R.figure("fig2_parity", "Parity relative to English, averaged over Indo-Aryan and Dravidian languages.", 5.8)
    R.heading_section("RQ1: The Sarvam lineage")
    R.para(f"Sarvam-1 devotes {v('vshare:pct:sarvam-1')}% of its 68K vocabulary to Indian scripts and reaches a mean "
           f"Indic fertility of {v('fertility:sarvam-1:indic')}. Sarvam-M uses the Mistral-Small-3.1 vocabulary "
           f"unchanged (all {v('lin:sarvamm_mistral:shared_string_and_id')} entries identical), so its fertility rises "
           f"to {v('fertility:sarvam-m:indic')}, reaching {v('fertility:sarvam-m:ory_Orya')} on Odia. The Sarvam-30B/105B "
           f"vocabulary shares {v('lin:sarvam30b_gemma3:shared_string_and_id')} entries "
           f"({v('lin:sarvam30b_gemma3:shared_pct')}%) with Gemma-3 at identical ids. Its "
           f"{v('lin:sarvam30b_gemma3:only_in_a')} new entries replace mainly CJK, Latin and Thai tokens with Gurmukhi, "
           "Odia, Kannada, Gujarati, Telugu and Malayalam tokens. Devanagari, Bengali and Tamil received none, so "
           "Sarvam-30B tokenizes Hindi, Marathi, Bengali, Assamese and Tamil exactly like Gemma-3.")
    R.figure("fig3_sarvam_evolution", "Fertility of the three Sarvam tokenizers with 95% bootstrap CIs.", 6.0)
    rows = [[LANGS[l]["name"], v(f"fertility:sarvam-1:{l}"), v(f"fertility:sarvam-30b:{l}"),
             v(f"wsv:p:fertility:{l}"), v(f"wsv:r:fertility:{l}")] for l in INDIC]
    R.table(["Language", "Sarvam-1", "Sarvam-30B", "p (Holm)", "r"], rows,
            "Sarvam-1 vs Sarvam-30B fertility (paired Wilcoxon; r < 0 means Sarvam-30B is higher)",
            widths=[1.4, 1.0, 1.0, 1.0, 0.8])
    R.para(f"Sarvam-30B is better on {v('wsv:n_b_better:fertility')} languages and worse on "
           f"{v('wsv:n_b_worse:fertility')}, including all four Dravidian ones; {v('wsv:n_sig:fertility')} of the 11 "
           "differences are significant.")
    R.heading_section("RQ2: Indo-Aryan vs Dravidian")
    R.para(f"Dravidian fertility is significantly higher for {v('wfam:n_dr_higher:fertility')} of "
           f"{v('wfam:n_total:fertility')} tokenizers. The ratio grows from {v('wfam:ratio:fertility:sarvam-1')} for "
           f"Sarvam-1 to {v('wfam:ratio:fertility:sarvam-30b')} for Sarvam-30B. Part of the gap is morphological "
           "(agglutinative words are longer and fewer). Parity, which controls for content, shows Dravidian text "
           f"costing more in only {v('wfam:n_dr_higher:parity')} tokenizers, mostly byte-level ones with few Indic "
           f"merges (Llama-3.1 ratio {v('wfam:ratio:parity:llama-3.1')}). Script coverage dominates family: Odia is "
           f"the most expensive language for GPT-4o (parity {v('parity:gpt-4o:ory_Orya')}) and Sarvam-M "
           f"({v('parity:sarvam-m:ory_Orya')}).")
    R.figure("fig8_effective_context", "Words that fit in an 8,192-token context window.", 6.0)
    R.heading_section("RQ3: Broken aksharas")
    R.para(f"GPT-4 splits {v('asr:gpt-4:indic')}% of aksharas, Llama-3.1 {v('asr:llama-3.1:indic')}% and Qwen2.5 "
           f"{v('asr:qwen-2.5:indic')}%, while GPT-4o splits {v('asr:gpt-4o:indic')}%, Sarvam-1 "
           f"{v('asr:sarvam-1:indic')}% and Sarvam-30B {v('asr:sarvam-30b:indic')}%. Sarvam-30B splits Dravidian "
           f"aksharas {v('wfam:ratio:asr:sarvam-30b')}× as often as Indo-Aryan ones; on Telugu, "
           f"{v('asr:sarvam-30b:tel_Telu')}% against {v('asr:sarvam-1:tel_Telu')}% for Sarvam-1.")
    R.figure("fig4_asr", "Akshara Split Rate by tokenizer and language family.", 6.0)
    R.figure("fig5_vocab_composition", "Vocabulary composition by script.", 6.4)
    R.heading_section("RQ4: Akshara-atomic BPE")
    rows = []
    for size in ("16k", "32k", "64k"):
        for k in (f"ours-bpe-{size}", f"ours-akshara-bpe-{size}"):
            rows.append([V[f"label:{k}"].replace("Ours ", ""), v(f"fertility:{k}:indic"), v(f"parity:{k}:indic"),
                         v(f"asr:{k}:indic"), v(f"pcw:{k}:indic"), V.get(f"train:mapped:{k}", "–")])
    rows.append(["Unigram 64K", v("fertility:ours-unigram-64k:indic"), v("parity:ours-unigram-64k:indic"),
                 v("asr:ours-unigram-64k:indic"), v("pcw:ours-unigram-64k:indic"), "–"])
    R.table(["Model", "Fertility", "Parity", "ASR %", "PCW", "Mapped"], rows,
            "Our tokenizers, mean over 11 Indian languages", widths=[1.6, 0.9, 0.8, 0.8, 0.7, 0.9])
    R.para(f"Akshara-atomic BPE reduces ASR from {v('asr:ours-bpe-64k:indic')}% to "
           f"{v('asr:ours-akshara-bpe-64k:indic')}% at 64K and from {v('asr:ours-bpe-16k:indic')}% to "
           f"{v('asr:ours-akshara-bpe-16k:indic')}% at 16K. Fertility rises by {v('rq4:fert_increase_pct:64k')}% and "
           f"{v('rq4:fert_increase_pct:16k')}% respectively. About {v('bare:extra_share_pct:64k')}% of the extra tokens at 64K "
           f"(and {v('bare:extra_share_pct:16k')}% at 16K) are standalone word-boundary tokens, which SentencePiece emits "
           "when an atomic akshara starts a word. No mapped akshara is ever split; the remaining splits "
           f"all fall on the {v('cov:oov_pct:ours-akshara-bpe-64k')}% of FLORES aksharas outside the 64K inventory. "
           f"Compared with Sarvam-1, the 64K akshara-atomic model has lower fertility "
           f"({v('fertility:ours-akshara-bpe-64k:indic')} vs {v('fertility:sarvam-1:indic')}) and a "
           f"{v('rq4:asr_ratio_sarvam1_over_ours64k')}× lower ASR, although its English fertility "
           f"({v('fertility:ours-bpe-64k:eng')}) is worse because it was trained on far less English.")
    R.figure("fig6_ours_vs_vocab", "Fertility and ASR against vocabulary size.", 6.2)
    R.heading_section("Discussion")
    R.para(f"For an 8K context, Llama-3.1 fits about {v('words_in_8k:llama-3.1:tel_Telu')} Telugu words against "
           f"{v('words_in_8k:sarvam-1:tel_Telu')} for Sarvam-1. Reusing a general vocabulary brings strong English "
           "and code coverage but inherits its gaps for scripts that receive no new entries. Limitations: whitespace "
           "words penalise agglutinative languages, FLORES is one domain, results are intrinsic only, the akshara "
           "rules approximate orthographic syllables, and our tokenizers were trained on a small corpus.")


def chapter6(R):
    R.heading_chapter("Conclusion and Future Work")
    R.para("Sarvam’s tokenizers moved from a dedicated Indic vocabulary (Sarvam-1), to an unchanged general "
           "vocabulary (Sarvam-M), to a lightly adapted Gemma-3 vocabulary (Sarvam-30B/105B). The last step helped "
           "several Indo-Aryan and low-resource scripts, but made all four Dravidian languages costlier and more "
           "often split than under Sarvam-1. Byte-level tokenizers without Indic merges break almost every akshara. "
           f"Akshara-atomic BPE removes splits of mapped aksharas entirely, at a {v('rq4:fert_increase_pct:64k')}"
           f"–{v('rq4:fert_increase_pct:16k')}% fertility cost.")
    R.para("Future work: train small language models on each tokenizer to measure downstream effects; add word-initial variants of atomic aksharas to remove standalone boundary tokens; add IN22 and "
           "conversational domains; combine akshara-atomic units with morphology-aware segmentation; and extend the "
           "analysis to the remaining scheduled languages and scripts.")


REFERENCES = [
    "R. Sennrich, B. Haddow, and A. Birch, “Neural machine translation of rare words with subword units,” in Proc. 54th Annu. Meeting ACL, 2016, pp. 1715–1725.",
    "T. Kudo, “Subword regularization: Improving neural network translation models with multiple subword candidates,” in Proc. 56th Annu. Meeting ACL, 2018, pp. 66–75.",
    "T. Kudo and J. Richardson, “SentencePiece: A simple and language independent subword tokenizer and detokenizer for neural text processing,” in Proc. EMNLP: System Demonstrations, 2018, pp. 66–71.",
    "OpenAI, “tiktoken,” GitHub repository. [Online]. Available: https://github.com/openai/tiktoken",
    "A. Grattafiori et al., “The Llama 3 herd of models,” arXiv:2407.21783, 2024.",
    "P. Rust, J. Pfeiffer, I. Vulić, S. Ruder, and I. Gurevych, “How good is your tokenizer? On the monolingual performance of multilingual language models,” in Proc. 59th Annu. Meeting ACL, 2021, pp. 3118–3135.",
    "A. Petrov, E. La Malfa, P. H. S. Torr, and A. Bibi, “Language model tokenizers introduce unfairness between languages,” in Advances in Neural Information Processing Systems 36, 2023, pp. 36963–36990.",
    "O. Ahia et al., “Do all languages cost the same? Tokenization in the era of commercial language models,” in Proc. EMNLP, 2023, pp. 9904–9923.",
    "V. Zouhar et al., “Tokenization and the noiseless channel,” in Proc. 61st Annu. Meeting ACL, 2023, pp. 5184–5207.",
    "D. Kakwani et al., “IndicNLPSuite: Monolingual corpora, evaluation benchmarks and pre-trained multilingual language models for Indian languages,” in Findings of EMNLP, 2020, pp. 4948–4961.",
    "S. Doddapaneni et al., “Towards leaving no Indic language behind: Building monolingual corpora, benchmark and models for Indic languages,” in Proc. 61st Annu. Meeting ACL, 2023, pp. 12402–12426.",
    "S. Khanuja et al., “MuRIL: Multilingual representations for Indian languages,” arXiv:2103.10730, 2021.",
    "J. Gala et al., “IndicTrans2: Towards high-quality and accessible machine translation models for all 22 scheduled Indian languages,” Trans. Mach. Learn. Res., 2023.",
    "M. S. U. R. Khan et al., “IndicLLMSuite: A blueprint for creating pre-training and fine-tuning datasets for Indian languages,” in Proc. 62nd Annu. Meeting ACL, 2024, pp. 15831–15879.",
    "N. Goyal et al., “The Flores-101 evaluation benchmark for low-resource and multilingual machine translation,” Trans. ACL, vol. 10, pp. 522–538, 2022.",
    "NLLB Team et al., “No language left behind: Scaling human-centered machine translation,” arXiv:2207.04672, 2022.",
    "M. Brahma et al., “Multilingual tokenization through the lens of Indian languages: Challenges and insights,” arXiv:2506.17789, 2025 (accepted to Findings of ACL 2026).",
    "M. Brahma et al., “MorphTok: Morphologically grounded tokenization for Indian languages,” arXiv:2504.10335, 2025 (TokShop, ICML 2025).",
    "S. Rana et al., “MUTANT: A recipe for multilingual tokenizer design,” arXiv:2511.03237, 2025.",
    "Sarvam AI, “Sarvam 1: the first Indian language LLM,” 24 Oct. 2024. [Online]. Available: https://www.sarvam.ai/blogs/sarvam-1",
    "Sarvam AI, “Sarvam-M multilingual language model,” 23 May 2025. [Online]. Available: https://www.sarvam.ai/blogs/sarvam-m",
    "Sarvam AI, “Open-sourcing Sarvam 30B & 105B models,” 6 Mar. 2026. [Online]. Available: https://www.sarvam.ai/blogs/sarvam-30b-105b",
    "Gemma Team et al., “Gemma 3 technical report,” arXiv:2503.19786, 2025.",
    "Qwen Team et al., “Qwen2.5 technical report,” arXiv:2412.15115, 2024.",
    "Mistral AI, “Mistral NeMo,” 18 Jul. 2024. [Online]. Available: https://mistral.ai/news/mistral-nemo",
    "A. Conneau et al., “Unsupervised cross-lingual representation learning at scale,” in Proc. 58th Annu. Meeting ACL, 2020, pp. 8440–8451.",
    "J. Devlin, M.-W. Chang, K. Lee, and K. Toutanova, “BERT: Pre-training of deep bidirectional transformers for language understanding,” in Proc. NAACL-HLT, 2019, pp. 4171–4186.",
    "The Unicode Consortium, “Unicode Standard Annex #29: Unicode text segmentation.” [Online]. Available: https://www.unicode.org/reports/tr29/",
]


def references(R):
    R.page_break()
    R.doc.add_heading("References", level=1)
    for i, ref in enumerate(REFERENCES, 1):
        p = R.doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.4)
        p.paragraph_format.first_line_indent = Inches(-0.4)
        p.paragraph_format.line_spacing = 1.15
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(f"[{i}]\t{ref}")
        r.font.size = Pt(11)


def appendix(R):
    R.page_break()
    R.doc.add_heading("Appendix A: Sample tokenizations", level=1)
    R.figure("fig7_token_visualisation", "One parallel FLORES sentence in Hindi and Telugu under five tokenizers. "
             "Red bars mark token boundaries inside an akshara; grey hex boxes are byte fragments.", 6.5)
    R.doc.add_heading("Appendix B: Full results", level=1)
    import pandas as pd
    s = pd.read_csv(ROOT / "results" / "benchmark_summary.csv")
    order = ["eng_Latn"] + INDO_ARYAN + DRAVIDIAN
    labels = s.drop_duplicates("tokenizer").set_index("tokenizer").label
    for metric, nd, cap in (("fertility", 2, "Fertility (tokens per word) for every tokenizer and language"),
                            ("asr", 1, "Akshara Split Rate (%) for every tokenizer and Indian language")):
        piv = s.pivot(index="tokenizer", columns="lang", values=metric)
        cols = order if metric == "fertility" else order[1:]
        rows = [[labels[k]] + [("" if pd.isna(piv.loc[k, c]) else f"{piv.loc[k, c]:.{nd}f}") for c in cols]
                for k in piv.index]
        R.table(["Tokenizer"] + [LANGS[c]["name"][:4] for c in cols], rows, cap,
                widths=[1.3] + [0.43] * len(cols), size=7)
    R.para("Language abbreviations use the first four letters of each language name. The complete long-format "
           "results, including parity, PCW, intra-character splits, Rényi efficiency and confidence intervals, are in "
           f"results/benchmark_long.csv and results/benchmark_summary.csv in the repository ({REPO}).")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "report" / "report.docx"))
    args = ap.parse_args()
    R = Report()
    front_matter(R)
    chapter1(R)
    chapter2(R)
    chapter3(R)
    chapter4(R)
    chapter5(R)
    chapter6(R)
    references(R)
    appendix(R)
    R.para(f"Code and data: {REPO}", italic=True, size=10)
    out = Path(args.out)
    out.parent.mkdir(exist_ok=True)
    R.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
