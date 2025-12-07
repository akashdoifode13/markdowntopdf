import streamlit as st
import markdown
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import re
from html.parser import HTMLParser

# ==========================================
# 1. CONFIGURATION: MAPPING CSS TO PYTHON
# ==========================================

# Colors from your CSS
H1_COLOR = '#2c3e50'
H2_COLOR = '#34495e'
H3_COLOR = '#455a64'
BODY_COLOR = '#000000'
CODE_INLINE_TEXT = '#e83e8c'
CODE_INLINE_BG = '#f0f0f0'
PRE_BLOCK_BG = '#2d2d2d'
PRE_BLOCK_TEXT = '#ffffff'
QUOTE_COLOR = '#666666'
TABLE_HEAD_BG = '#f4f4f4'
TABLE_BORDER = '#dddddd'

# Fonts
# Logic: Try to register Barlow/FiraCode. If files missing, fallback to Helvetica/Courier.
try:
    # If you have the .ttf files in the same folder, this works.
    # Otherwise it falls back to the except block.
    pdfmetrics.registerFont(TTFont('Barlow', 'Barlow-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('Barlow-Bold', 'Barlow-Bold.ttf'))
    pdfmetrics.registerFont(TTFont('FiraCode', 'FiraCode-Regular.ttf'))
    BODY_FONT = 'Barlow'
    HEAD_FONT = 'Barlow-Bold'
    MONO_FONT = 'FiraCode'
except:
    BODY_FONT = 'Helvetica'
    HEAD_FONT = 'Helvetica-Bold'
    MONO_FONT = 'Courier'

# ==========================================
# 2. MARKDOWN PROCESSING
# ==========================================

def preprocess_markdown(text):
    """Fixes Markdown list spacing for the parser."""
    lines = text.split('\n')
    result = []
    for i, line in enumerate(lines):
        # Detect lists
        is_list = bool(re.match(r'^[\s]*[\*\-]\s', line)) or bool(re.match(r'^[\s]*\d+\.\s', line))
        # Ensure blank line before list starts
        if is_list and i > 0 and lines[i-1].strip() != '':
            result.append('')
        result.append(line)
    return '\n'.join(result)

def add_footer(canvas, doc):
    """Adds a footer to every page."""
    canvas.saveState()
    page_width, page_height = A4
    canvas.setFont(BODY_FONT, 8)
    canvas.setFillColor(colors.HexColor('#888888'))
    canvas.drawString(2 * cm, 1.0 * cm, "Generated Report")
    canvas.drawRightString(page_width - 2 * cm, 1.0 * cm, f"Page {doc.page}")
    canvas.restoreState()

# ==========================================
# 3. HTML TO PDF PARSER
# ==========================================

class CSSStyleParser(HTMLParser):
    def __init__(self, styles):
        super().__init__()
        self.styles = styles
        self.story = []
        self.current_text = []
        
        # State tracking
        self.list_stack = [] # Stores 'ul' or 'ol'
        self.list_counters = [] # Stores integers for 'ol'
        self.in_pre = False     # Inside <pre> block
        
        # Table tracking
        self.in_table = False
        self.rows = []
        self.curr_row = []
        self.curr_cell = []
        self.in_th = False

    def handle_starttag(self, tag, attrs):
        # Flush existing text before starting a block element
        if tag in ['h1', 'h2', 'h3', 'p', 'ul', 'ol', 'li', 'table', 'blockquote', 'pre']:
            self.flush()

        if tag == 'ul':
            self.list_stack.append('ul')
        elif tag == 'ol':
            self.list_stack.append('ol')
            self.list_counters.append(0)
        elif tag == 'li':
            if self.list_stack and self.list_stack[-1] == 'ol':
                self.list_counters[-1] += 1
        
        elif tag == 'table':
            self.in_table = True
            self.rows = []
        elif tag == 'tr':
            self.curr_row = []
        elif tag in ['td', 'th']:
            self.curr_cell = []
            self.in_th = (tag == 'th')
            
        elif tag == 'pre':
            self.in_pre = True
            
        elif tag == 'code':
            # CSS: :not(pre)>code
            if not self.in_pre:
                self.current_text.append(f'<font face="{MONO_FONT}" color="{CODE_INLINE_TEXT}" backColor="{CODE_INLINE_BG}">')
        
        elif tag in ['strong', 'b']:
            self.current_text.append('<b>')
        elif tag in ['em', 'i']:
            self.current_text.append('<i>')
            
        elif tag == 'br':
            if self.in_table:
                self.curr_cell.append('<br/>')
            else:
                self.current_text.append('<br/>')

    def handle_endtag(self, tag):
        # Flush text when closing block elements
        if tag in ['h1', 'h2', 'h3', 'p', 'li', 'blockquote', 'pre']:
            self.flush(tag)

        if tag == 'ul':
            self.list_stack.pop()
            if not self.list_stack: self.story.append(Spacer(1, 8))
        elif tag == 'ol':
            self.list_stack.pop()
            self.list_counters.pop()
            if not self.list_stack: self.story.append(Spacer(1, 8))
            
        elif tag == 'pre':
            self.in_pre = False
            
        elif tag == 'code':
            if not self.in_pre:
                self.current_text.append('</font>')
                
        elif tag in ['strong', 'b']:
            self.current_text.append('</b>')
        elif tag in ['em', 'i']:
            self.current_text.append('</i>')
            
        elif tag == 'table':
            self.build_table()
            self.in_table = False
        elif tag == 'tr':
            if self.curr_row: self.rows.append(self.curr_row)
        elif tag in ['td', 'th']:
            content = "".join(self.curr_cell).strip()
            if not content: content = "&nbsp;"
            
            # Select style based on TH or TD
            style = self.styles['CustomTH'] if self.in_th else self.styles['CustomTD']
            self.curr_row.append(Paragraph(content, style))

    def handle_data(self, data):
        if self.in_table:
            self.curr_cell.append(data)
        else:
            self.current_text.append(data)
            
    def handle_entityref(self, name):
        char = f'&{name};'
        if self.in_table: self.curr_cell.append(char)
        else: self.current_text.append(char)

    def flush(self, tag=None):
        text = "".join(self.current_text).strip()
        if not text: return
        self.current_text = []
        
        # XML Escape for ReportLab
        text = text.replace('&', '&amp;')

        if tag == 'h1':
            self.story.append(Paragraph(text, self.styles['CustomH1']))
        elif tag == 'h2':
            self.story.append(Paragraph(text, self.styles['CustomH2']))
        elif tag == 'h3':
            self.story.append(Paragraph(text, self.styles['CustomH3']))
        elif tag == 'blockquote':
            self.story.append(Paragraph(text, self.styles['CustomQuote']))
        elif tag == 'pre':
            # Handle newlines in code blocks
            text = text.replace('\n', '<br/>')
            self.story.append(Paragraph(text, self.styles['CustomPre']))
        elif tag == 'li':
            # List Logic
            level = len(self.list_stack)
            indent = (level - 1) * 20 + 10
            if self.list_stack[-1] == 'ol':
                bullet = f"{self.list_counters[-1]}."
            else:
                bullet = "•"
            
            style = ParagraphStyle(
                'ListItem', parent=self.styles['CustomBody'],
                leftIndent=indent+15, firstLineIndent=-15, spaceAfter=2
            )
            self.story.append(Paragraph(f"{bullet} {text}", style))
        elif tag == 'p':
            self.story.append(Paragraph(text, self.styles['CustomBody']))

    def build_table(self):
        if not self.rows: return
        cols = len(self.rows[0])
        if cols == 0: return
        
        # Calculate width
        avail_width = 17 * cm
        col_width = avail_width / cols
        
        t = Table(self.rows, colWidths=[col_width]*cols, repeatRows=1)
        
        # CSS: border: 1px solid #ddd; th { background-color: #f4f4f4 }
        style_cmds = [
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor(TABLE_BORDER)),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor(TABLE_HEAD_BG)),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]
        t.setStyle(TableStyle(style_cmds))
        self.story.append(Spacer(1, 12))
        self.story.append(t)
        self.story.append(Spacer(1, 12))

# ==========================================
# 4. STYLES DEFINITION
# ==========================================

def get_css_styles():
    """Create ParagraphStyles that strictly match the CSS provided."""
    styles = getSampleStyleSheet()
    
    # Base Body
    styles.add(ParagraphStyle(
        name='CustomBody',
        parent=styles['Normal'],
        fontName=BODY_FONT,
        fontSize=11,
        leading=11 * 1.6, # CSS line-height: 1.6
        textColor=colors.HexColor(BODY_COLOR),
        spaceAfter=12,
        alignment=TA_LEFT
    ))

    # Headings
    styles.add(ParagraphStyle(
        name='CustomH1',
        parent=styles['Normal'],
        fontName=HEAD_FONT,
        fontSize=26, # ~2.2em
        leading=32,
        textColor=colors.HexColor(H1_COLOR),
        spaceBefore=24, spaceAfter=12,
        keepWithNext=True
    ))
    
    styles.add(ParagraphStyle(
        name='CustomH2',
        parent=styles['Normal'],
        fontName=HEAD_FONT,
        fontSize=22, # ~1.8em
        leading=28,
        textColor=colors.HexColor(H2_COLOR),
        spaceBefore=20, spaceAfter=10,
        keepWithNext=True
    ))
    
    styles.add(ParagraphStyle(
        name='CustomH3',
        parent=styles['Normal'],
        fontName=HEAD_FONT,
        fontSize=17, # ~1.4em
        leading=22,
        textColor=colors.HexColor(H3_COLOR),
        spaceBefore=16, spaceAfter=8,
        keepWithNext=True
    ))

    # Blockquote
    styles.add(ParagraphStyle(
        name='CustomQuote',
        parent=styles['Normal'],
        fontName=BODY_FONT,
        fontSize=11,
        leading=11 * 1.6,
        textColor=colors.HexColor(QUOTE_COLOR),
        leftIndent=15, # Indentation
        spaceAfter=12
    ))

    # Pre/Code Block
    styles.add(ParagraphStyle(
        name='CustomPre',
        parent=styles['Normal'],
        fontName=MONO_FONT,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor(PRE_BLOCK_TEXT),
        backColor=colors.HexColor(PRE_BLOCK_BG),
        borderPadding=10, # CSS padding
        spaceAfter=12,
        splitLongWords=True
    ))

    # Table Cells
    styles.add(ParagraphStyle(
        name='CustomTD',
        parent=styles['Normal'],
        fontName=BODY_FONT,
        fontSize=10,
        leading=14,
        textColor=colors.black
    ))
    
    styles.add(ParagraphStyle(
        name='CustomTH',
        parent=styles['Normal'],
        fontName=HEAD_FONT,
        fontSize=10,
        leading=14,
        textColor=colors.black,
        alignment=TA_CENTER
    ))

    return styles

# ==========================================
# 5. MAIN CONVERSION FUNCTION
# ==========================================

def markdown_to_pdf(md_text):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )
    
    # Preprocess and Convert to HTML
    clean_md = preprocess_markdown(md_text)
    # 'extra' enables tables, fenced code blocks, etc.
    html_content = markdown.markdown(clean_md, extensions=['extra'])
    
    # Parse HTML to PDF Elements
    styles = get_css_styles()
    parser = CSSStyleParser(styles)
    parser.feed(html_content)
    
    # Build PDF
    doc.build(parser.story, onFirstPage=add_footer, onLaterPages=add_footer)
    
    buffer.seek(0)
    return buffer

# ==========================================
# 6. STREAMLIT UI
# ==========================================

def main():
    st.set_page_config(page_title="CSS Styled PDF Generator", layout="wide")
    
    st.title("🎨 CSS-to-PDF Generator")
    st.markdown("This tool converts markdown to PDF using the **exact styling** specified.")

    col1, col2 = st.columns([1, 1])

    default_text = """# Project Alpha Status
**Client:** Acme Corp | **Date:** Oct 2025

## Executive Summary
The project is on track. We are adhering to the new styling guidelines.

> "Design is not just what it looks like and feels like. Design is how it works."

### Technical Implementation
We are using the following loop structure:

def optimize_process(data):
for item in data:
# Process item
print(f"Processing {item}")
return True

Inline code looks like `api_key = "123"` and `user_id`.

### Resource Allocation

| Role | Count | Allocation |
| :--- | :--- | :--- |
| Backend Dev | 4 | 100% |
| Frontend Dev | 3 | 100% |
| QA Engineer | 2 | 50% |
"""

    with col1:
        st.subheader("📝 Input Markdown")
        md_input = st.text_area("Type your markdown here:", value=default_text, height=600)

    with col2:
        st.subheader("👁️ Preview (Styled)")
        # Injecting CSS to make the preview match the PDF output
        st.markdown(f"""
        <style>
            h1 {{ color: {H1_COLOR} !important; border-bottom: 2px solid #eee; padding-bottom: 0.5rem; }}
            h2 {{ color: {H2_COLOR} !important; }}
            h3 {{ color: {H3_COLOR} !important; }}
            p {{ line-height: 1.6; color: {BODY_COLOR}; }}
            code {{ background-color: {CODE_INLINE_BG}; color: {CODE_INLINE_TEXT}; padding: 2px 4px; border-radius: 3px; }}
            pre {{ background-color: {PRE_BLOCK_BG}; padding: 10px; border-radius: 4px; }}
            pre code {{ color: {PRE_BLOCK_TEXT}; background-color: transparent; }}
            blockquote {{ border-left: 4px solid #ddd; padding-left: 1em; color: {QUOTE_COLOR}; }}
            th {{ background-color: {TABLE_HEAD_BG}; border: 1px solid {TABLE_BORDER}; }}
            td {{ border: 1px solid {TABLE_BORDER}; }}
        </style>
        """, unsafe_allow_html=True)
        st.markdown(md_input, unsafe_allow_html=True)

    st.divider()

    if st.button("⬇️ Generate PDF", type="primary"):
        try:
            pdf_file = markdown_to_pdf(md_input)
            st.download_button(
                label="Download Final PDF",
                data=pdf_file,
                file_name="styled_report.pdf",
                mime="application/pdf"
            )
            st.success("PDF created successfully!")
        except Exception as e:
            st.error(f"Error generating PDF: {e}")

if __name__ == "__main__":
    main()