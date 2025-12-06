import streamlit as st
import markdown
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_JUSTIFY, TA_CENTER
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import re
from html.parser import HTMLParser
import html as html_module

# Register DejaVu Sans fonts (similar to Barlow used in Ideal PDF)
try:
    pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    FONT_REGULAR = 'DejaVuSans'
    FONT_BOLD = 'DejaVuSans-Bold'
except:
    FONT_REGULAR = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'

# Colors matching Ideal PDF
HEADING_COLOR = '#1a4a5e'  # Dark teal/blue for H2, H3
BODY_COLOR = '#333333'


def preprocess_markdown(text):
    """
    Fix markdown list formatting - add blank line before lists when needed.
    This is required because markdown lists need a blank line before them
    to be properly detected when they follow other content.
    """
    lines = text.split('\n')
    result = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check if this line starts a list item (including indented ones)
        is_list_item = bool(re.match(r'^[\s]*[\*\-]\s', line)) or bool(re.match(r'^[\s]*\d+\.\s', line))
        
        if is_list_item and i > 0:
            prev_line = lines[i-1]
            prev_stripped = prev_line.strip()
            # Check if previous line is NOT empty and NOT a list item
            prev_is_list = bool(re.match(r'^[\s]*[\*\-]\s', prev_line)) or bool(re.match(r'^[\s]*\d+\.\s', prev_line))
            
            if prev_stripped and not prev_is_list:
                # Add blank line before this list item
                result.append('')
        
        result.append(line)
    
    return '\n'.join(result)


def add_page_footer(canvas, doc):
    """Add footer to each page"""
    canvas.saveState()
    page_width, page_height = A4
    canvas.setFont(FONT_REGULAR, 9)
    canvas.setFillColor(colors.HexColor('#666666'))
    canvas.drawRightString(
        page_width - 1.5 * cm,
        1.5 * cm,
        "Powered by Draup"
    )
    canvas.restoreState()


class MarkdownHTMLParser(HTMLParser):
    """Parser matching Ideal PDF styling"""
    def __init__(self, styles):
        super().__init__()
        self.styles = styles
        self.story = []
        self.current_text = []
        self.text_stack = []
        self.in_list = False
        self.list_level = 0
        self.list_type_stack = []
        self.list_counter = []
        
        self.in_table = False
        self.in_thead = False
        self.in_tbody = False
        self.in_tr = False
        self.in_td = False
        self.in_th = False
        self.table_data = []
        self.current_row = []
        self.current_cell = []
        
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.flush_text()
            self.in_table = True
            self.table_data = []
        elif tag == 'thead':
            self.in_thead = True
        elif tag == 'tbody':
            self.in_tbody = True
        elif tag == 'tr':
            self.in_tr = True
            self.current_row = []
        elif tag == 'th':
            self.in_th = True
            self.current_cell = []
        elif tag == 'td':
            self.in_td = True
            self.current_cell = []
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.flush_text()
            self.text_stack.append(tag)
        elif tag in ['strong', 'b']:
            self.current_text.append('<b>')
        elif tag in ['em', 'i']:
            self.current_text.append('<i>')
        elif tag == 'code':
            self.current_text.append('<font face="Courier" size="10">')
        elif tag == 'ul':
            self.flush_text()
            self.in_list = True
            self.list_level += 1
            self.list_type_stack.append('ul')
        elif tag == 'ol':
            self.flush_text()
            self.in_list = True
            self.list_level += 1
            self.list_type_stack.append('ol')
            self.list_counter.append(0)
        elif tag == 'li':
            self.flush_text()
            if self.list_type_stack and self.list_type_stack[-1] == 'ol':
                self.list_counter[-1] += 1
        elif tag == 'br':
            if self.in_td or self.in_th:
                self.current_cell.append('\n')
            else:
                self.current_text.append('<br/>')
        elif tag == 'p':
            self.flush_text()
        elif tag == 'hr':
            self.flush_text()
            self.story.append(Spacer(1, 12))
            
    def handle_endtag(self, tag):
        if tag == 'table':
            self.create_table()
            self.in_table = False
        elif tag == 'thead':
            self.in_thead = False
        elif tag == 'tbody':
            self.in_tbody = False
        elif tag == 'tr':
            if self.current_row:
                self.table_data.append(self.current_row)
            self.current_row = []
            self.in_tr = False
        elif tag == 'th':
            cell_text = ''.join(self.current_cell).strip()
            self.current_row.append(cell_text)
            self.current_cell = []
            self.in_th = False
        elif tag == 'td':
            cell_text = ''.join(self.current_cell).strip()
            self.current_row.append(cell_text)
            self.current_cell = []
            self.in_td = False
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.flush_text(heading_tag=tag)
            if self.text_stack and self.text_stack[-1] == tag:
                self.text_stack.pop()
        elif tag in ['strong', 'b']:
            self.current_text.append('</b>')
        elif tag in ['em', 'i']:
            self.current_text.append('</i>')
        elif tag == 'code':
            self.current_text.append('</font>')
        elif tag == 'ul':
            self.in_list = self.list_level > 1
            self.list_level -= 1
            if self.list_type_stack:
                self.list_type_stack.pop()
            if self.list_level == 0:
                self.story.append(Spacer(1, 10))
        elif tag == 'ol':
            self.in_list = self.list_level > 1
            self.list_level -= 1
            if self.list_type_stack:
                self.list_type_stack.pop()
            if self.list_counter:
                self.list_counter.pop()
            if self.list_level == 0:
                self.story.append(Spacer(1, 10))
        elif tag == 'li':
            self.flush_text(is_list_item=True)
        elif tag == 'p':
            self.flush_text()
    
    def handle_entityref(self, name):
        """Handle HTML entities like &amp; -> &"""
        try:
            char = html_module.unescape(f'&{name};')
        except:
            char = f'&{name};'
        if self.in_td or self.in_th:
            self.current_cell.append(char)
        else:
            self.current_text.append(char)
            
    def handle_charref(self, name):
        """Handle numeric character references"""
        try:
            char = html_module.unescape(f'&#{name};')
        except:
            char = f'&#{name};'
        if self.in_td or self.in_th:
            self.current_cell.append(char)
        else:
            self.current_text.append(char)
            
    def handle_data(self, data):
        if self.in_td or self.in_th:
            self.current_cell.append(data)
        else:
            self.current_text.append(data)
    
    def create_table(self):
        """Create table matching Ideal PDF - white header, box border"""
        if not self.table_data:
            return
        
        num_cols = len(self.table_data[0]) if self.table_data else 0
        if num_cols == 0:
            return
        
        available_width = 17 * cm
        col_widths = [available_width / num_cols] * num_cols
        
        formatted_data = []
        for i, row in enumerate(self.table_data):
            formatted_row = []
            for cell in row:
                # Escape & for reportlab XML parsing
                safe_cell = cell.replace('&', '&amp;')
                if i == 0:
                    para = Paragraph(f"<b>{safe_cell}</b>", self.styles['TableHeader'])
                else:
                    para = Paragraph(safe_cell, self.styles['TableCell'])
                formatted_row.append(para)
            formatted_data.append(formatted_row)
        
        table = Table(formatted_data, colWidths=col_widths, repeatRows=1)
        
        # Ideal PDF style: WHITE header background, BOX border around table
        table.setStyle(TableStyle([
            # Header - WHITE background with BOLD text
            ('BACKGROUND', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            
            # Body
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#333333')),
            ('FONTNAME', (0, 1), (-1, -1), FONT_REGULAR),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            
            # BOX border around entire table
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            
            # Line below header
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#cccccc')),
            
            # Horizontal lines between rows
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor('#e0e0e0')),
            
            # Vertical lines between columns
            ('LINEBEFORE', (1, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        self.story.append(Spacer(1, 16))
        self.story.append(table)
        self.story.append(Spacer(1, 16))
        self.table_data = []
        
    def flush_text(self, heading_tag=None, is_list_item=False):
        if not self.current_text:
            return
            
        text = ''.join(self.current_text).strip()
        if not text:
            self.current_text = []
            return
        
        # Escape & for reportlab XML parsing
        safe_text = text.replace('&', '&amp;')
        
        if is_list_item or self.in_list:
            # Different bullet for different levels (matching Ideal PDF)
            # Level 1: • (filled circle)
            # Level 2+: ◦ (hollow circle)
            if self.list_level == 1:
                bullet = "•"
                indent = 28
            else:
                bullet = "◦"
                indent = 28 + (self.list_level - 1) * 24
            
            para_style = ParagraphStyle(
                'BulletItem',
                parent=self.styles['Normal'],
                leftIndent=indent,
                firstLineIndent=-14,
                spaceBefore=5,
                spaceAfter=5,
                fontSize=12,
                leading=18,
                fontName=FONT_REGULAR,
            )
            bullet_text = f"{bullet}  {safe_text}"
            self.story.append(Paragraph(bullet_text, para_style))
        elif heading_tag:
            style_name = f'Custom{heading_tag.upper()}'
            self.story.append(Paragraph(safe_text, self.styles[style_name]))
            spacing = {'h1': 16, 'h2': 14, 'h3': 12, 'h4': 10, 'h5': 8, 'h6': 8}
            self.story.append(Spacer(1, spacing.get(heading_tag, 10)))
        else:
            self.story.append(Paragraph(safe_text, self.styles['CustomBody']))
            self.story.append(Spacer(1, 10))
            
        self.current_text = []


def create_styles():
    """Create styles matching Ideal PDF"""
    styles = getSampleStyleSheet()
    
    # Body - 12pt with good line spacing
    styles.add(ParagraphStyle(
        name='CustomBody',
        parent=styles['Normal'],
        fontName=FONT_REGULAR,
        fontSize=12,
        leading=20,
        textColor=colors.HexColor(BODY_COLOR),
        alignment=TA_LEFT,
        spaceAfter=10,
        spaceBefore=0
    ))
    
    # H1 - Black (main title)
    styles.add(ParagraphStyle(
        name='CustomH1',
        fontName=FONT_BOLD,
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=10,
        spaceBefore=20,
        alignment=TA_LEFT,
        keepWithNext=True
    ))
    
    # H2 - BLUE/TEAL (section headers like "Executive Summary", "Market Signals")
    styles.add(ParagraphStyle(
        name='CustomH2',
        fontName=FONT_BOLD,
        fontSize=18,
        leading=24,
        textColor=colors.HexColor(HEADING_COLOR),
        spaceAfter=10,
        spaceBefore=20,
        alignment=TA_LEFT,
        keepWithNext=True
    ))
    
    # H3 - BLUE/TEAL (subsection headers like "M&A & Partnerships", "Executive Movements")
    styles.add(ParagraphStyle(
        name='CustomH3',
        fontName=FONT_BOLD,
        fontSize=15,
        leading=20,
        textColor=colors.HexColor(HEADING_COLOR),
        spaceAfter=8,
        spaceBefore=16,
        alignment=TA_LEFT,
        keepWithNext=True
    ))
    
    # H4
    styles.add(ParagraphStyle(
        name='CustomH4',
        fontName=FONT_BOLD,
        fontSize=13,
        leading=18,
        textColor=colors.HexColor('#2a5a6e'),
        spaceAfter=6,
        spaceBefore=14,
        alignment=TA_LEFT,
        keepWithNext=True
    ))
    
    # H5 & H6
    styles.add(ParagraphStyle(
        name='CustomH5',
        fontName=FONT_BOLD,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#3a6a7e'),
        spaceAfter=5,
        spaceBefore=12,
        alignment=TA_LEFT
    ))
    
    styles.add(ParagraphStyle(
        name='CustomH6',
        fontName=FONT_BOLD,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#4a7a8e'),
        spaceAfter=5,
        spaceBefore=10,
        alignment=TA_LEFT
    ))
    
    # Table styles - white background, clean look
    styles.add(ParagraphStyle(
        name='TableHeader',
        fontName=FONT_BOLD,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#333333'),
        alignment=TA_LEFT
    ))
    
    styles.add(ParagraphStyle(
        name='TableCell',
        fontName=FONT_REGULAR,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#333333'),
        alignment=TA_LEFT
    ))
    
    return styles


def markdown_to_pdf(markdown_text):
    """Convert markdown to PDF matching Ideal PDF style"""
    # Preprocess markdown to fix list formatting issues
    fixed_markdown = preprocess_markdown(markdown_text)
    
    # Convert to HTML (removed nl2br extension which was breaking list detection)
    html_content = markdown.markdown(
        fixed_markdown,
        extensions=['extra', 'sane_lists', 'tables']
    )
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm
    )
    
    styles = create_styles()
    parser = MarkdownHTMLParser(styles)
    parser.feed(html_content)
    story = parser.story
    
    doc.build(story, onFirstPage=add_page_footer, onLaterPages=add_page_footer)
    
    buffer.seek(0)
    return buffer


def main():
    st.set_page_config(
        page_title="Markdown to PDF Converter",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    st.title("📄 Markdown to PDF Converter")
    st.markdown("Convert your markdown to **professional PDFs** matching the Ideal format.")
    
    with st.expander("💡 Features (Matching Ideal PDF)", expanded=False):
        st.markdown("""
        ### Typography
        - Body: DejaVuSans 12pt
        - H1: Bold 24pt (Black)
        - H2/H3: Bold 18pt/15pt (Blue/Teal #1a4a5e)
        
        ### Bullet Points
        - Level 1: • (filled circle)
        - Level 2+: ◦ (hollow circle) with proper indentation
        - **Fixed:** Lists after bold text now render correctly
        
        ### Tables
        - White header background (not gray)
        - Box border around entire table
        - Vertical column separators
        - Clean, professional look
        
        ### Formatting
        - A4 page size with 2cm margins
        - "Powered by Draup" footer on every page
        - Proper spacing and line heights
        """)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 Input Markdown")
        markdown_text = st.text_area(
            "Paste your markdown here:",
            height=550,
            placeholder="""# ABM Intelligence Report: L'Oréal

**Prepared for:** Inetum | **Date:** 12-06-2025

## Executive Summary

**Target Account Overview:** L'Oréal is a global leader...

### Deal Activity

**Target Account Engagements:**
* L'Oréal recently engaged Capgemini for a large-scale Cloud migration project.
* IBM was awarded a contract for AI model development.

**Competitive Landscape:**
* **Capgemini:** Winning large infrastructure and cloud deals.
* **IBM:** Winning high-value AI/Data science deals (C3).
* **Accenture:** Remains the incumbent for high-level strategy.

Your content here...""",
            help="Professional PDF matching Ideal format"
        )
    
    with col2:
        st.subheader("👁️ Live Preview")
        if markdown_text:
            st.markdown(markdown_text)
        else:
            st.info("Your markdown preview will appear here")
    
    st.divider()
    
    if markdown_text:
        col_info, col_btn, col_space = st.columns([2, 1, 1])
        
        with col_info:
            st.markdown("""
            **📋 Your PDF will include:**
            - ✨ Blue/teal headings (H2, H3)
            - ✨ Proper bullet points (• and ◦)
            - ✨ Clean tables with box borders
            - ✨ A4 format with 2cm margins
            - ✨ "Powered by Draup" footer
            """)
        
        with col_btn:
            try:
                pdf_buffer = markdown_to_pdf(markdown_text)
                st.download_button(
                    label="⬇️ Download PDF",
                    data=pdf_buffer,
                    file_name="document.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
                st.success("✅ PDF Ready!")
            except Exception as e:
                st.error(f"Error: {str(e)}")
                with st.expander("Show details"):
                    st.exception(e)
    else:
        st.info("👆 Enter markdown text above to generate your PDF")


if __name__ == "__main__":
    main()