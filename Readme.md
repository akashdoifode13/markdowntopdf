# 🎨 CSS-Styled Markdown to PDF Generator

A professional PDF generation tool built with **Python**, **Streamlit**, and **ReportLab**. 

This application takes standard Markdown text and converts it into a PDF that follows strict CSS-like styling rules (custom typography, colors, table borders, and code block formatting).

## 🚀 Features

*   **Live Preview:** See how your Markdown looks with the applied CSS styles immediately in the browser.
*   **Custom Typography:** Supports **Barlow** (Body/Headings) and **Fira Code** (Monospace) fonts.
    *   *Includes automatic fallback to Helvetica/Courier if font files are missing.*
*   **CSS-to-PDF Mapping:**
    *   **Headings:** Custom colors (`#2c3e50`, `#34495e`) and underlining styles.
    *   **Code Blocks:** Dark theme (`#2d2d2d`) for blocks, Pink (`#e83e8c`) on Grey for inline code.
    *   **Tables:** Styled with light grey headers (`#f4f4f4`) and subtle borders.
    *   **Blockquotes:** Indented with a visual border.
*   **Robust Parsing:** Handles Markdown lists, nested formatting, and HTML entities correctly.

## 🛠️ Installation & Setup

### 1. Clone or Download
Download the `app.py` file to your local machine.

### 2. Install Dependencies
Create a virtual environment (optional but recommended) and install the required Python packages:

```bash
pip install streamlit markdown reportlab
```

### 3. (Optional) Add Custom Fonts
To achieve the **exact** look defined in the CSS (Barlow and Fira Code), you need to place the `.ttf` files in the same directory as `app.py`.

1.  Download **Barlow** (Regular and Bold) from [Google Fonts](https://fonts.google.com/specimen/Barlow).
2.  Download **Fira Code** (Regular) from [Google Fonts](https://fonts.google.com/specimen/Fira+Code).
3.  Rename/Place them in your folder so they match these filenames exactly:
    *   `Barlow-Regular.ttf`
    *   `Barlow-Bold.ttf`
    *   `FiraCode-Regular.ttf`

*Note: If these files are not found, the app will automatically default to standard PDF fonts (Helvetica and Courier).*

## ▶️ Usage

Run the Streamlit application:

```bash
streamlit run app.py
```

Your browser will open automatically.
1.  **Left Panel:** Paste your Markdown text.
2.  **Right Panel:** View the HTML styled preview.
3.  **Button:** Click **"⬇️ Generate PDF"** to download the result.

## 🎨 Configuration

You can easily change the "CSS" styles by modifying the constants at the top of `app.py`.

```python
# MAPPING CSS TO PYTHON
H1_COLOR = '#2c3e50'
H2_COLOR = '#34495e'
BODY_COLOR = '#000000'
CODE_INLINE_TEXT = '#e83e8c'
# ... etc
```

## 📋 Project Structure

```text
├── app.py                # Main application script
├── README.md             # Documentation
├── Barlow-Regular.ttf    # (Optional) Custom Font
├── Barlow-Bold.ttf       # (Optional) Custom Font
└── FiraCode-Regular.ttf  # (Optional) Custom Font
```

## 📦 Requirements

*   Python 3.8+
*   Streamlit
*   Markdown
*   ReportLab

## 🤝 Troubleshooting

*   **"KeyError: Style already defined":** This version of the code handles style naming conflicts by using unique prefixes (`CustomBody`, `CustomH1`). It is safe to restart the app.
*   **Fonts look standard:** Ensure the `.ttf` files are in the *exact same folder* where you are running the terminal command, and that the filenames match exactly what is in the code.

---
**Generated with ❤️ using Streamlit & ReportLab**
