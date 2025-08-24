import streamlit as st
from pathlib import Path
from streamlit.components.v1 import html as html_component

st.set_page_config(page_title="Anxiety AI", layout="wide")
html_path = Path(__file__).with_suffix(".html")
if not html_path.exists():
    html_path = Path(__file__).parent / "3_Anxiety_AI.html"

html = html_path.read_text(encoding="utf-8")
BACKEND_URL = "https://thrivehub-a85v.onrender.com"
html = f"<script>window.BACKEND = '{BACKEND_URL}';</script>" + html
html_component(html, height=900, scrolling=True)