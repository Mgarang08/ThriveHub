import streamlit as st
from pathlib import Path
from streamlit.components.v1 import html as html_component

st.set_page_config(page_title="Anxiety AI", layout="wide")

# --- Find the companion HTML file (same stem as this .py) ---
html_path = Path(__file__).with_suffix(".html")
if not html_path.exists():
    # Fallback if your HTML has a different name — change as needed
    html_path = Path(__file__).parent / "3_Anxiety_AI.html"

html = html_path.read_text(encoding="utf-8")

BACKEND_URL = "http://127.0.0.1:5000"

# Inject a global for the iframe
html = f"<script>window.BACKEND = '{BACKEND_URL}';</script>" + html

# Render the HTML
html_component(html, height=900, scrolling=True)