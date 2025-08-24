import streamlit as st
from dataclasses import dataclass
from typing import Dict
from streamlit.components.v1 import html as html_component


st.set_page_config(page_title="ThriveHub", layout="wide")


MULTIPAGE_MODE = True
PAGES = {
   "Budgeter": "1_Budgeter.py",
   "Culinary Quest": "2_Culinary_Quest.py",
   "Anxiety AI": "3_Anxiety_AI.py",
}
APP_URLS: Dict[str, str] = {
   "Budgeter": "http://localhost:8601",
   "Culinary Quest": "http://localhost:8602",
   "Anxiety AI": "http://localhost:8603",
}


# ────────── Enhanced Gradient CSS with smaller icons ──────────
st.markdown("""
<style>
body {background: linear-gradient(135deg, #f5f7fa, #c3cfe2);}


.block-container {max-width: 1100px; padding-top: 2rem;}


.hero {
   text-align: center;
   padding: 2rem 1rem;
   background: linear-gradient(135deg, #667eea, #764ba2);
   border-radius: 24px;
   color: #fff;
   box-shadow: 0 8px 30px rgba(0,0,0,.1);
}


.hero h1 {
   font-size: 3rem;
   font-weight: 900;
   background: linear-gradient(90deg,#ff9a9e,#fad0c4,#a18cd1);
   -webkit-background-clip: text;
   -webkit-text-fill-color: transparent;
   margin-bottom: 0.3rem;
}


.hero p {
   font-size: 1.2rem;
   color: #f3f3f3;
}


.grid {
   display: grid;
   grid-template-columns: 1fr;
   gap: 20px;
}
@media (min-width: 980px) { .grid {grid-template-columns: repeat(3, 1fr);} }


.card {
   border-radius: 24px;
   padding: 16px;
   background: linear-gradient(145deg,#f6f8ff,#e0e7ff);
   box-shadow: 0 8px 25px rgba(0,0,0,.08);
   transition: transform .2s ease, box-shadow .2s ease;
}
.card:hover { transform: translateY(-6px); box-shadow: 0 14px 35px rgba(0,0,0,.12); }


.title { font-size: 1.3rem; font-weight: 700; margin-bottom: 4px; }
.desc { font-size: 0.95rem; color: #4b5563; margin-bottom: 10px; }


.stButton>button {
   background: linear-gradient(135deg,#667eea,#764ba2);
   color: white;
   font-weight: 600;
   border-radius: 12px;
   padding: 10px 0;
   width: 100%;
   transition: transform .2s ease;
}
.stButton>button:hover { transform: scale(1.03); }


.svgwrap { width: 50px; height: 50px; flex-shrink: 0; }
</style>
""", unsafe_allow_html=True)


# ────────── Inline SVGs ──────────
def svg_budgeter(): return """
<svg viewBox="0 0 200 200" class="svgwrap" xmlns="http://www.w3.org/2000/svg">
 <defs><linearGradient id="g1" x1="0" x2="1"><stop offset="0" stop-color="#8ec5fc"/><stop offset="1" stop-color="#e0c3fc"/></linearGradient></defs>
 <rect x="10" y="50" rx="24" ry="24" width="180" height="110" fill="url(#g1)"/>
 <circle cx="60" cy="105" r="22" fill="#ffffff"/>
 <circle cx="60" cy="105" r="12" fill="#111827"/>
 <rect x="80" y="65" width="40" height="12" rx="6" fill="#111827" opacity=".85"/>
 <circle cx="155" cy="85" r="12" fill="#111827" opacity=".12"/>
 <text x="100" y="135" font-size="28" text-anchor="middle" fill="#111827" opacity=".9">$</text>
</svg>"""


def svg_culinary(): return """
<svg viewBox="0 0 200 200" class="svgwrap" xmlns="http://www.w3.org/2000/svg">
 <defs><linearGradient id="g2" x1="0" x2="1"><stop offset="0" stop-color="#f6d365"/><stop offset="1" stop-color="#fda085"/></linearGradient></defs>
 <rect x="20" y="25" width="160" height="100" rx="18" fill="url(#g2)"/>
 <path d="M80 120 h40 v20 a10 10 0 0 1 -10 10 h-20 a10 10 0 0 1 -10 -10z" fill="#111827"/>
 <path d="M60 75 a40 32 0 0 1 80 0 c0 10 -8 18 -18 18 H78 c-10 0 -18 -8 -18 -18z" fill="#fff"/>
 <circle cx="150" cy="50" r="6" fill="#111827" opacity=".15"/>
</svg>"""


def svg_anxiety(): return """
<svg viewBox="0 0 200 200" class="svgwrap" xmlns="http://www.w3.org/2000/svg">
 <defs><linearGradient id="g3" x1="0" x2="1"><stop offset="0" stop-color="#a1ffce"/><stop offset="1" stop-color="#faffd1"/></linearGradient></defs>
 <rect x="18" y="40" width="164" height="120" rx="22" fill="url(#g3)"/>
 <path d="M100 75 c22 -22 60 8 30 34 l-30 26 -30 -26 c-30 -26 8 -56 30 -34z" fill="#ffffff" stroke="#111827" stroke-width="2"/>
 <circle cx="45" cy="60" r="8" fill="#111827" opacity=".12"/>
</svg>"""


# ────────── Data ──────────
@dataclass
class AppCard:
   name: str
   description: str
   svg: str


APPS = [
   AppCard("Budgeter","Track spending, set goals, and visualize progress at a glance.", svg_budgeter()),
   AppCard("Culinary Quest","Step-by-step recipe journeys with clean vector illustrations.", svg_culinary()),
   AppCard("Anxiety AI","Guided breathing, CBT-style prompts, and calm check-ins.", svg_anxiety()),
]


# ────────── Functions ──────────
def launch_single(app_name):
   if MULTIPAGE_MODE:
       page = PAGES.get(app_name)
       if page: st.switch_page(f"pages/{page}")
       else: st.error(f"Page not found: pages/{page}")
   else:
       url = APP_URLS.get(app_name)
       if url: html_component(f"<script>window.open('{url}','_blank');</script>",0)
       else: st.error("APP_URLS missing for this app.")


# ────────── Hero ──────────
st.markdown("""
<div class="hero">
 <h1>ThriveHub</h1>
 <p>Your trio of tools — plan money, cook smart, and care for your mind.</p>
</div>
""", unsafe_allow_html=True)


# ────────── Cards Grid ──────────
st.markdown('<div class="grid">', unsafe_allow_html=True)
for app in APPS:
   with st.container():
       st.markdown(f'''
       <div class="card">
         <div style="display:flex;align-items:center;gap:12px;">
           <div class="svgwrap">{app.svg}</div>
           <div>
             <p class="title">{app.name}</p>
             <p class="desc">{app.description}</p>
           </div>
         </div>
       </div>
       ''', unsafe_allow_html=True)
       if st.button(f"Open {app.name}", key=f"open_{app.name}", use_container_width=True):
           launch_single(app.name)
st.markdown('</div>', unsafe_allow_html=True)
