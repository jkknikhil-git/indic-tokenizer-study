"""Submission document: input data links + result outcome screenshots + key figures.

Writes submission/results_and_input_data.docx. Usage: python scripts/build_results_doc.py
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/jkknikhil-git/indic-tokenizer-study"
FONT = "Times New Roman"

DATA = [
    ("Evaluation data", "FLORES-200 devtest (12 languages x 1,012 parallel sentences)",
     "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"),
    ("Training data", "AI4Bharat Sangraha, verified split (50,000 sentences per language, streamed)",
     "https://huggingface.co/datasets/ai4bharat/sangraha"),
    ("Corpus statistics", "Sentence counts, filtering and overlap removal per language",
     f"{REPO}/blob/main/results/corpus_stats.json"),
    ("Run metadata", "Library versions, seeds, dataset sources, tokenizer revisions",
     f"{REPO}/blob/main/results/run_metadata.json"),
    ("Code and results", "Full repository (one-command reproduction)", REPO),
]
TOKENIZERS = [
    ("Sarvam-1", "https://huggingface.co/sarvamai/sarvam-1"),
    ("Sarvam-M", "https://huggingface.co/sarvamai/sarvam-m"),
    ("Sarvam-30B", "https://huggingface.co/sarvamai/sarvam-30b"),
    ("Sarvam-105B", "https://huggingface.co/sarvamai/sarvam-105b"),
    ("GPT-4o / GPT-4 (tiktoken o200k_base, cl100k_base)", "https://github.com/openai/tiktoken"),
    ("Llama-3.1 (public mirror)", "https://huggingface.co/unsloth/Llama-3.1-8B"),
    ("Gemma-3 (public mirror)", "https://huggingface.co/unsloth/gemma-3-1b-it"),
    ("Qwen2.5", "https://huggingface.co/Qwen/Qwen2.5-7B"),
    ("MuRIL", "https://huggingface.co/google/muril-base-cased"),
    ("IndicBERTv2", "https://huggingface.co/ai4bharat/IndicBERTv2-MLM-only"),
    ("XLM-R", "https://huggingface.co/FacebookAI/xlm-roberta-base"),
    ("mBERT", "https://huggingface.co/google-bert/bert-base-multilingual-cased"),
]
SHOTS = [
    ("01_tests", "Automated tests: all 77 pass (akshara segmentation, metrics, round-trip)."),
    ("02_final_check", "Consistency check: random numbers quoted in the paper recomputed from raw data; all figures current."),
    ("03_key_results", "Key results on FLORES-200: fertility, parity and Akshara Split Rate for every tokenizer."),
    ("04_vocab_lineage", "Vocabulary lineage: Sarvam-30B vs Gemma-3 and Sarvam-M vs Mistral-Small-3.1."),
    ("05_sarvam1_vs_sarvam30b", "Sarvam-1 vs Sarvam-30B fertility per language (paired Wilcoxon, Holm-corrected)."),
    ("06_indo_aryan_vs_dravidian", "Indo-Aryan vs Dravidian fertility per tokenizer (paired Wilcoxon)."),
    ("07_our_tokenizers", "Our tokenizers: training time, mapped aksharas, fertility and Akshara Split Rate."),
]
FIGS = [
    ("fig1_fertility_heatmap", "Fertility (tokens per word) for every tokenizer and language."),
    ("fig3_sarvam_evolution", "Fertility of the three Sarvam tokenizers with 95% bootstrap CIs."),
    ("fig4_asr", "Akshara Split Rate by tokenizer, Indo-Aryan vs Dravidian."),
    ("fig6_ours_vs_vocab", "Akshara-atomic BPE vs standard BPE across vocabulary sizes."),
    ("fig7_token_visualisation", "How five tokenizers split the same Hindi and Telugu sentence."),
]


def hyperlink(paragraph, url, text=None, size=10):
    r_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    for tag, attrs in (("w:rFonts", {"w:ascii": FONT, "w:hAnsi": FONT}), ("w:color", {"w:val": "1F5FBF"}),
                       ("w:u", {"w:val": "single"}), ("w:sz", {"w:val": str(size * 2)})):
        el = OxmlElement(tag)
        for k, v in attrs.items():
            el.set(qn(k), v)
        rpr.append(el)
    run.append(rpr)
    t = OxmlElement("w:t")
    t.text = text or url
    run.append(t)
    h.append(run)
    paragraph._p.append(h)


def cell_text(cell, text, bold=False, size=10):
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(12)


def picture(doc, path, width):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True  # never separate an image from its caption
    p.add_run().add_picture(str(path), width=Inches(width))


def main():
    doc = Document()
    sec = doc.sections[0]
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Inches(0.8))
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(11)
    for name in ("Title", "Heading 1"):
        h = doc.styles[name]
        h.font.name = FONT
        h.font.color.rgb = RGBColor(0, 0, 0)
        h.element.get_or_add_rPr()

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("Results and Input Data")
    r.bold = True
    r.font.size = Pt(18)
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("Measuring the Indic Tokenizer Tax: A Comparative Study of Sarvam AI's Tokenizers and "
                  "Akshara-Aware Subword Segmentation for Indian Languages")
    r.bold = True
    r.font.size = Pt(12)
    info = doc.add_table(rows=0, cols=2)
    info.style = "Table Grid"
    info.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in (("Name", "Nikhileshwar Jakka"), ("Reg. No.", "23FE10CII00213"),
                 ("Course", "Natural Language Processing (NLP)"), ("Guide", "Heena Kalim"),
                 ("Programme", "B.Tech CSE (IoT & Intelligent Systems), Manipal University Jaipur")):
        c = info.add_row().cells
        cell_text(c[0], k, bold=True)
        cell_text(c[1], v)
        c[0].width, c[1].width = Inches(1.4), Inches(5.4)
    p = doc.add_paragraph()
    p.add_run("GitHub repository: ").bold = True
    hyperlink(p, REPO, size=11)

    doc.add_heading("1. Input data links", level=1)
    tab = doc.add_table(rows=1, cols=3)
    tab.style = "Table Grid"
    for i, h in enumerate(("Item", "Description", "Link")):
        cell_text(tab.rows[0].cells[i], h, bold=True)
    for item, desc, url in DATA:
        c = tab.add_row().cells
        cell_text(c[0], item, bold=True)
        cell_text(c[1], desc)
        hyperlink(c[2].paragraphs[0], url, size=9)
    for row in tab.rows:
        for c, w in zip(row.cells, (1.3, 2.6, 2.9)):
            c.width = Inches(w)
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.add_run("Tokenizers evaluated (tokenizer files only; no model weights were downloaded):").bold = True
    tab = doc.add_table(rows=1, cols=2)
    tab.style = "Table Grid"
    cell_text(tab.rows[0].cells[0], "Tokenizer", bold=True)
    cell_text(tab.rows[0].cells[1], "Source", bold=True)
    for name, url in TOKENIZERS:
        c = tab.add_row().cells
        cell_text(c[0], name)
        hyperlink(c[1].paragraphs[0], url, size=9)
    for row in tab.rows:
        row.cells[0].width, row.cells[1].width = Inches(3.0), Inches(3.8)

    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.add_heading("2. Result outcome screenshots", level=1)
    doc.add_paragraph("Each screenshot is the captured output of running the command shown at its top in the "
                      "project folder (regenerate with: python scripts/make_screenshots.py).")
    for i, (name, cap) in enumerate(SHOTS, 1):
        picture(doc, ROOT / "screenshots" / f"{name}.png", 6.8)
        caption(doc, f"Screenshot {i}: {cap}")

    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.add_heading("3. Result figures", level=1)
    for i, (name, cap) in enumerate(FIGS, 1):
        picture(doc, ROOT / "figures" / f"{name}.png", 6.6 if name != "fig4_asr" else 6.0)
        caption(doc, f"Figure {i}: {cap}")

    out = ROOT / "submission" / "results_and_input_data.docx"
    out.parent.mkdir(exist_ok=True)
    doc.save(out)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
