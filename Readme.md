# Markdown to PDF Converter

A Streamlit web application that converts markdown text to PDF with a custom footer "Powered by Draup" on every page.

## Features

- 📝 Paste markdown text in the input area
- 👁️ Live preview of your markdown
- 📄 Convert to PDF with one click
- 🔖 Automatic footer "Powered by Draup" on every page (bottom right corner)
- ✨ Supports common markdown features:
  - Headings (H1-H6)
  - Bold and italic text
  - Lists (bulleted and numbered)
  - Inline code
  - Line breaks

## Installation

### Option 1: Automated Setup (Recommended)

Run the setup script:
```bash
chmod +x setup.sh
./setup.sh
```

Then run the app:
```bash
./run.sh
```

### Option 2: Manual Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install the required packages:
```bash
pip install streamlit reportlab markdown
```

## Usage

### Quick Start
```bash
./run.sh
```

### Manual Start
```bash
source venv/bin/activate  # Activate virtual environment
streamlit run markdown_to_pdf.py
```

2. Open your browser (usually opens automatically at http://localhost:8501)

3. Paste your markdown text in the left panel

4. See the live preview in the right panel

5. Click "Download PDF" to get your PDF file

## Example Markdown

```markdown
# My Document

## Introduction

This is a **bold** statement and this is *italic*.

### Key Points

- First point
- Second point
- Third point

## Conclusion

This document was created with the Markdown to PDF converter.
```

## Notes

- The footer "Powered by Draup" appears on every page in the bottom right corner
- The app uses ReportLab for PDF generation
- Markdown is converted to HTML first, then to PDF

## Requirements

- Python 3.7+
- streamlit
- reportlab
- markdown

## License

Free to use and modify.