# app.py — Culinary Quest (v13: richer offline food illustrations + stable navigation)

import streamlit as st
from dataclasses import dataclass
from typing import List, Dict, Any
from pathlib import Path
import json, textwrap
from streamlit.components.v1 import html as html_component
import requests

BACKEND = "http://127.0.0.1:5000"

st.set_page_config(page_title="Culinary Quest", layout="wide")

# ---------- CSS ----------
st.markdown(
    """
    <style>
      .block-container {max-width: 860px; padding-top: 1.6rem;}  /* was .5rem */
      .sticky-top {position: sticky; top: 0; z-index: 999; background: #fff;
                   padding: .4rem 0 .35rem; border-bottom: 1px solid rgba(0,0,0,.06);}    
      .stButton>button {border-radius: 9999px; padding: .7rem 1.1rem; font-size: 1.05rem;
                        box-shadow: 0 2px 8px rgba(0,0,0,.06); border: 1px solid rgba(0,0,0,.08);}

      /* Title tweaks to avoid clipping on some browsers/zooms */
      .title {text-align:center; margin: .5rem 0 .75rem; line-height: 1.2;}  /* +margin, +line-height */
      .subtitle {text-align:center; color:#6b7280; margin-top: 0;}
      .badge {display:inline-block; padding: .15rem .5rem; border-radius: 999px;
              background:#eef2ff; color:#3730a3; font-size: .8rem}
      .card {border: 1px solid #e5e7eb; border-radius: 14px; padding: .75rem; margin-bottom: .5rem;}
      .card h4 {margin: 0 0 .25rem;}
      .steptext {text-align:center; font-size: 1.02rem; margin-top: .4rem}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Data ----------
@dataclass
class Recipe:
    name: str
    steps: List[str]
    time_min: int

BUILTIN: Dict[str, Recipe] = {
    "Sandwich": Recipe("Sandwich", [
        "Lay out two slices of bread.",
        "Add fillings (cheese/meat/veg).",
        "Add sauce or spread.",
        "Close and press gently.",
        "Cut and serve.",
    ], 6),
    "Oatmeal": Recipe("Oatmeal", [
        "Bring milk or water to a simmer.",
        "Stir in oats.",
        "Cook 3–5 minutes, stirring occasionally.",
        "Sweeten and add toppings.",
        "Serve warm.",
    ], 7),
    "Omelete": Recipe("Omelete", [
        "Whisk eggs with a pinch of salt.",
        "Pour into a buttered pan on medium-low.",
        "When almost set, add fillings.",
        "Fold over and cook 30–60 sec.",
        "Slide onto a plate and serve.",
    ], 8),
    "Grilled Cheese Sandwich": Recipe("Grilled Cheese Sandwich", [
        "Butter the outside of two bread slices.",
        "Place cheese between the unbuttered sides.",
        "Heat pan on medium and add sandwich.",
        "Cook 2–3 min each side until golden and melty.",
        "Rest 1 minute, slice diagonally, serve.",
    ], 8),
    "Fruit Salad": Recipe("Fruit Salad", [
        "Rinse and dry all fruit.",
        "Chop fruit into bite-size pieces.",
        "Add a squeeze of lemon and a teaspoon of honey.",
        "Gently toss to coat evenly.",
        "Chill 5 minutes and serve.",
    ], 10),
    "Cheese Quesadilla": Recipe("Cheese Quesadilla", [
        "Place tortilla in a pan over medium heat.",
        "Sprinkle cheese evenly over tortilla.",
        "Fold tortilla in half.",
        "Cook 2–3 min per side until cheese melts.",
        "Cut into wedges and serve.",
    ], 7),
    "Pasta Marinara": Recipe("Pasta Marinara", [
        "Boil salted water and cook pasta al dente.",
        "Warm marinara in a pan; add a splash of pasta water.",
        "Drain pasta and toss with sauce.",
        "Finish with olive oil and basil.",
        "Plate and sprinkle with parmesan.",
    ], 18),
}

def _from_obj(obj: Dict[str, Any]) -> Dict[str, Recipe]:
    out: Dict[str, Recipe] = {}
    for k, v in obj.items():
        try:
            name = v.get("name", k)
            steps = [str(s) for s in v.get("steps", [])]
            if not steps:
                continue
            time_min = int(v.get("time_min", max(5, len(steps) * 2)))
            out[name] = Recipe(name, steps, time_min)
        except Exception:
            continue
    return out

def load_user_recipes_file(path: Path) -> Dict[str, Recipe]:
    try:
        if not path.exists() or not path.is_file():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return _from_obj(data)
        if isinstance(data, list):
            obj = {r.get("name", f"Recipe {i+1}"): r for i, r in enumerate(data) if isinstance(r, dict)}
            return _from_obj(obj)
    except Exception:
        pass
    return {}

def get_all_recipes() -> Dict[str, Recipe]:
    recipes: Dict[str, Recipe] = dict(BUILTIN)
    for p in [
        Path("recipes.json"),
        Path("data/recipes.json"),
        Path("assets/recipes.json"),
        Path("original_recipes.json"),
        Path("originals.json"),
    ]:
        recipes.update(load_user_recipes_file(p))
    d = Path("recipes")
    if d.exists():
        for jf in sorted(d.glob("*.json")):
            recipes.update(load_user_recipes_file(jf))
    return recipes

# ---------- Offline SVG step illustrations ----------
def svg_html(svg: str, height: int = 320):
    html_component(svg, height=height, scrolling=False)

def wrap_lines(text: str, width: int = 44) -> List[str]:
    return textwrap.wrap(text, width=width)[:3]

def kind_from_text(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["chop", "slice", "cut", "dice"]): return "chop"
    if any(k in t for k in ["boil", "simmer", "water", "al dente"]): return "boil"
    if any(k in t for k in ["pan", "toast", "sear", "fry", "griddle", "butter", "golden"]): return "pan"
    if any(k in t for k in ["mix", "toss", "combine", "bowl", "stir"]): return "mix"
    if any(k in t for k in ["serve", "plate", "cut"]): return "serve"
    return "prep"

def scene(recipe: str, text: str) -> str:
    """Return a detailed SVG <g> that includes FOOD + tools based on recipe + step text."""
    r = recipe.lower()
    k = kind_from_text(text)

    # shared shapes
    plate = "<ellipse cx='500' cy='220' rx='200' ry='26' fill='#e2e8f0'/>"
    steam = (
        "<g opacity='.8' fill='none' stroke='#94a3b8' stroke-width='3'>"
        "<path d='M420 110 q20 -20 0 -40'/>"
        "<path d='M455 110 q20 -20 0 -40'/>"
        "<path d='M490 110 q20 -20 0 -40'/>"
        "</g>"
    )

    if "sandwich" in r:
        bread_bottom = "<rect x='390' y='170' width='220' height='40' rx='10' fill='#fef3c7' stroke='#f59e0b'/>"
        bread_top    = "<rect x='390' y='140' width='220' height='38' rx='10' fill='#fde68a' stroke='#f59e0b'/>"
        cheese       = "<rect x='410' y='160' width='180' height='16' rx='4' fill='#facc15'/>"
        lettuce      = "<path d='M410 182 q20 -12 40 0 t40 0 t40 0 t40 0' fill='#22c55e'/>"
        tomato1      = "<circle cx='445' cy='172' r='8' fill='#ef4444'/>"
        tomato2      = "<circle cx='505' cy='172' r='8' fill='#ef4444'/>"
        sauce        = "<path d='M430 150 q30 10 60 0 q30 -10 60 0' fill='#f43f5e' opacity='.7'/>"

        if "add fillings" in r or "fillings" in text.lower():
            return plate + bread_bottom + cheese + lettuce + tomato1 + tomato2
        if "sauce" in text.lower() or "spread" in text.lower():
            return plate + bread_bottom + sauce
        if "close" in text.lower() or "press" in text.lower():
            arrow = "<polygon points='610,150 640,165 610,180' fill='#334155'/>"
            return plate + bread_bottom + cheese + lettuce + tomato1 + tomato2 + arrow + bread_top
        if "cut" in text.lower() or "serve" in text.lower():
            tri1 = "<polygon points='470,160 610,160 540,220' fill='#fde68a' stroke='#f59e0b'/>"
            tri2 = "<polygon points='470,160 400,220 540,220' fill='#f59e0b' opacity='.35'/>"
            return plate + tri1 + tri2
        # lay out bread
        return plate + bread_top + bread_bottom

    if "quesadilla" in r:
        tortilla   = "<circle cx='500' cy='180' r='90' fill='#fde68a' stroke='#eab308'/>"
        cheese     = "<path d='M500 100 l70 80 l-140 0 z' fill='#facc15' opacity='.9'/>"
        pan        = "<rect x='360' y='200' width='280' height='34' rx='18' fill='#475569'/><rect x='620' y='208' width='80' height='10' rx='5' fill='#475569'/>"
        if "fold" in text.lower():
            fold = "<path d='M500 90 q90 90 0 180 q-90 -90 0 -180' fill='#fef08a' opacity='.9'/>"
            return pan + tortilla + cheese + fold
        if "cut" in text.lower() or "serve" in text.lower():
            wedge = "<path d='M500 90 A90 90 0 0 1 590 180 L500 180 Z' fill='#facc15'/>"
            return plate + tortilla + wedge
        return pan + tortilla + cheese + steam

    if "oat" in r:
        bowl = "<ellipse cx='500' cy='210' rx='160' ry='24' fill='#cbd5e1'/><path d='M360 180 q140 80 280 0 v30 q-140 80 -280 0 z' fill='#e2e8f0'/>"
        oats = "<ellipse cx='500' cy='175' rx='140' ry='26' fill='#fde68a' stroke='#f59e0b'/>"
        berries = "<circle cx='460' cy='170' r='8' fill='#ef4444'/><circle cx='515' cy='178' r='7' fill='#a855f7'/><circle cx='550' cy='170' r='6' fill='#ef4444'/>"
        spoon = "<rect x='580' y='120' width='14' height='70' rx='7' fill='#9ca3af'/><circle cx='587' cy='118' r='12' fill='#9ca3af'/>"
        pot = "<rect x='420' y='140' width='160' height='60' rx='8' fill='#64748b'/><rect x='450' y='120' width='100' height='18' rx='8' fill='#64748b'/>"
        if "simmer" in text.lower():
            return pot + steam
        if "stir" in text.lower():
            return bowl + oats + spoon
        if "sweeten" in text.lower() or "toppings" in text.lower():
            honey = "<path d='M400 120 q30 20 60 0 q30 -20 60 0' stroke='#f59e0b' stroke-width='6' fill='none'/>"
            return bowl + oats + berries + honey
        return bowl + oats + berries

    if "omelet" in r or "omelete" in r or "omelette" in r:
        pan = "<rect x='360' y='200' width='280' height='36' rx='18' fill='#475569'/><rect x='620' y='208' width='80' height='10' rx='5' fill='#475569'/>"
        eggs = "<ellipse cx='460' cy='150' rx='26' ry='20' fill='#fef3c7' stroke='#f59e0b'/><ellipse cx='510' cy='150' rx='26' ry='20' fill='#fef3c7' stroke='#f59e0b'/>"
        whisk = "<rect x='560' y='120' width='8' height='70' rx='4' fill='#9ca3af'/><path d='M564 120 q-18 12 -18 40 q0 28 18 40 q18 -12 18 -40 q0 -28 -18 -40' fill='none' stroke='#9ca3af' stroke-width='4'/>"
        fold = "<path d='M420 180 q80 -60 160 0 q-80 60 -160 0' fill='#fde68a' stroke='#f59e0b'/>"
        fill = "<circle cx='500' cy='170' r='8' fill='#10b981'/><rect x='520' y='166' width='26' height='10' rx='5' fill='#facc15'/>"
        if "whisk" in text.lower():
            return eggs + whisk + plate
        if "add fillings" in text.lower() or "fillings" in text.lower():
            return pan + fold + fill
        if "fold" in text.lower():
            return pan + fold + steam
        if "slide" in text.lower() or "serve" in text.lower():
            half = "<path d='M440 170 q60 -40 120 0 q-60 40 -120 0' fill='#fde68a' stroke='#f59e0b'/>"
            return plate + half + fill
        return pan + fold

    if "pasta" in r or "marinara" in r:
        pot = "<rect x='400' y='140' width='200' height='70' rx='10' fill='#475569'/><rect x='430' y='120' width='140' height='20' rx='8' fill='#475569'/>"
        noodles = "".join(f"<rect x='{420+i*16}' y='146' width='10' height='60' rx='5' fill='#fde68a'/>" for i in range(10))
        sauce = "<rect x='430' y='150' width='140' height='20' rx='8' fill='#ef4444' opacity='.9'/>"
        ladle = "<rect x='580' y='120' width='10' height='60' rx='5' fill='#9ca3af'/><circle cx='585' cy='185' r='12' fill='#9ca3af'/>"
        if "boil" in text.lower() or "al dente" in text.lower():
            return pot + noodles + steam
        if "toss" in text.lower() or "sauce" in text.lower() or "marinara" in text.lower():
            return pot + noodles + sauce + ladle
        if "finish" in text.lower():
            basil = "<path d='M470 150 q10 -10 20 0 q-10 10 -20 0' fill='#22c55e'/>"
            return pot + noodles + sauce + basil
        if "plate" in text.lower() or "serve" in text.lower():
            nest = "<circle cx='500' cy='180' r='70' fill='#fde68a' opacity='.9'/><path d='M440 180 q60 30 120 0' stroke='#f59e0b' stroke-width='6' fill='none'/>"
            return plate + nest + "<circle cx='500' cy='180' r='18' fill='#ef4444'/>"
        return pot + noodles

    if "fruit" in r:
        board = "<rect x='370' y='150' width='260' height='70' rx='12' fill='#fcd34d' stroke='#f59e0b'/>"
        kiwi  = "<circle cx='410' cy='185' r='16' fill='#22c55e'/><circle cx='410' cy='185' r='6' fill='#065f46'/>"
        berry = "<circle cx='450' cy='178' r='10' fill='#ef4444'/>"
        banana= "<ellipse cx='520' cy='188' rx='26' ry='12' fill='#fde68a' stroke='#f59e0b'/>"
        bowl  = "<ellipse cx='500' cy='230' rx='170' ry='22' fill='#cbd5e1'/><path d='M330 200 q170 80 340 0 v30 q-170 80 -340 0 z' fill='#e2e8f0'/>"
        if "chop" in text.lower() or "slice" in text.lower():
            knife = "<rect x='575' y='160' width='12' height='60' rx='6' fill='#94a3b8'/><rect x='560' y='180' width='30' height='12' rx='6' fill='#374151'/>"
            return board + kiwi + berry + banana + knife
        if "toss" in text.lower() or "mix" in text.lower():
            spoon = "<rect x='590' y='160' width='12' height='60' rx='6' fill='#94a3b8'/><circle cx='596' cy='156' r='10' fill='#94a3b8'/>"
            fruit = "<circle cx='480' cy='205' r='10' fill='#ef4444'/><circle cx='520' cy='210' r='10' fill='#22c55e'/>"
            return bowl + fruit + spoon
        return board + kiwi + berry + banana

    # generic prep/mix/pan scenes
    if k == "chop":
        board = "<rect x='380' y='150' width='240' height='70' rx='12' fill='#fcd34d' stroke='#f59e0b'/>"
        knife = "<rect x='585' y='160' width='12' height='60' rx='6' fill='#94a3b8'/><rect x='568' y='178' width='32' height='12' rx='6' fill='#374151'/>"
        veg1  = "<rect x='410' y='175' width='16' height='16' rx='4' fill='#22c55e'/>"
        veg2  = "<rect x='440' y='175' width='16' height='16' rx='4' fill='#ef4444'/>"
        return board + veg1 + veg2 + knife
    if k == "pan":
        pan = "<rect x='360' y='200' width='280' height='36' rx='18' fill='#475569'/><rect x='620' y='208' width='80' height='10' rx='5' fill='#475569'/>"
        food= "<rect x='450' y='188' width='100' height='10' rx='5' fill='#facc15'/>"
        return pan + food + steam
    if k == "boil":
        pot = "<rect x='400' y='140' width='200' height='70' rx='10' fill='#475569'/><rect x='430' y='120' width='140' height='20' rx='8' fill='#475569'/>"
        bubbles = "".join(f"<circle cx='{440+i*24}' cy='168' r='5' fill='#e2e8f0'/>" for i in range(8))
        return pot + bubbles + steam
    if k == "mix":
        bowl = "<ellipse cx='500' cy='210' rx='160' ry='24' fill='#cbd5e1'/><path d='M360 180 q140 80 280 0 v30 q-140 80 -280 0 z' fill='#e2e8f0'/>"
        spoon= "<rect x='580' y='120' width='14' height='70' rx='7' fill='#9ca3af'/><circle cx='587' cy='118' r='12' fill='#9ca3af'/>"
        dots = "<circle cx='480' cy='180' r='6' fill='#f59e0b'/><circle cx='520' cy='186' r='6' fill='#ef4444'/>"
        return bowl + dots + spoon
    # prep
    plate = "<ellipse cx='500' cy='220' rx='200' ry='26' fill='#e2e8f0'/>"
    knife = "<rect x='590' y='160' width='12' height='60' rx='6' fill='#94a3b8'/><rect x='572' y='178' width='32' height='12' rx='6' fill='#374151'/>"
    return plate + knife

def step_svg(recipe: str, step_idx: int, total: int, text: str) -> str:
    lines = wrap_lines(text, 44)
    lines_svg = "".join(
        f"<text x='500' y='{250 + i*24}' text-anchor='middle' font-family='Inter, system-ui' font-size='18' fill='#0f172a'>{line}</text>"
        for i, line in enumerate(lines)
    )
    safe_title = recipe.replace("&", "&amp;")
    return f"""
    <div style='display:flex;justify-content:center'>
    <svg viewBox='0 0 1000 360' xmlns='http://www.w3.org/2000/svg' role='img' aria-label='{safe_title} step'>
      <defs>
        <linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>
          <stop offset='0%' stop-color='#f8fafc'/>
          <stop offset='100%' stop-color='#eef2ff'/>
        </linearGradient>
        <filter id='d' x='-10%' y='-10%' width='120%' height='120%'>
          <feDropShadow dx='0' dy='2' stdDeviation='10' flood-color='#000' flood-opacity='0.12'/>
        </filter>
      </defs>
      <rect x='16' y='16' width='968' height='308' rx='20' fill='url(#bg)' filter='url(#d)'/>
      <text x='40' y='58' font-family='Inter, system-ui' font-size='18' fill='#334155'>Step {step_idx} of {total} — {safe_title}</text>
      {scene(recipe, text)}
      {lines_svg}
    </svg>
    </div>
    """

# ---------- State ----------
if "screen" not in st.session_state:      st.session_state.screen = "home"
if "recipe_key" not in st.session_state:  st.session_state.recipe_key = None
if "step_idx" not in st.session_state:    st.session_state.step_idx = 0
if "ingredients" not in st.session_state: st.session_state.ingredients = []

# ---------- Navigation ----------
def load_recipe(key: str):
    st.session_state.recipe_key = key
    st.session_state.step_idx = 0
    st.session_state.screen = "recipe"

def go_home():  st.session_state.screen = "home"

def next_step():
    recipes = _all_recipes_with_ai()
    r = recipes[st.session_state.recipe_key]
    st.session_state.step_idx = min(st.session_state.step_idx + 1, len(r.steps) - 1)

def prev_step():
    st.session_state.step_idx = max(st.session_state.step_idx - 1, 0)

# ---------- Command Panel ----------
def _normalize_ingredients_state():
    """Ensure session ingredients are a simple list[str] of names."""
    raw = st.session_state.get("ingredients", [])
    normalized = []
    for it in raw:
        if isinstance(it, dict):
            nm = (it.get("name") or "").strip()
            if nm:
                normalized.append(nm)
        elif isinstance(it, str):
            nm = it.strip()
            if nm:
                normalized.append(nm)
    st.session_state.ingredients = normalized

def _keyify(s: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in s)[:32] or "x"

import re

def _parse_dish_name(recipe_text: str) -> str:
    # 1) Look for "DISH NAME: ..."
    m = re.search(r'(?im)^\s*(?:dish\s*name|title)\s*:\s*(.+?)\s*$', recipe_text)
    if m:
        return m.group(1).strip()

    # 2) Otherwise take the first non-empty line (without bullet/number prefixes)
    for ln in (ln.strip() for ln in recipe_text.splitlines()):
        if not ln:
            continue
        ln = re.sub(r'^(?:\d+\.\s*|-\s*|•\s*)', '', ln)  # strip "1. ", "- ", "• "
        if ln:
            return ln[:80].strip()

    return "Unnamed Recipe"

def command_panel_ui(scope: str):
    _normalize_ingredients_state()

    with st.form(f"cmd_form_{scope}", clear_on_submit=True):
        ing_block = st.text_area(
            "Add ingredients (one per line or comma/semicolon-separated)",
            key=f"ing_block_{scope}",
            height=140,
            placeholder="bread\ncheddar cheese\nlettuce\ntomato",
        )
        single = st.text_input(
            "Or add one ingredient",
            key=f"ing_single_{scope}",
            placeholder="e.g., olive oil",
        )

        colA, colB = st.columns(2)
        add_btn = colA.form_submit_button("Add to List", use_container_width=True)
        api_btn = colB.form_submit_button("🔎 Get Recipe", use_container_width=True)

        # ---- Parse freshly typed inputs
        import re
        names = []
        if ing_block:
            tokens = re.split(r"[,;\n\r]+", ing_block)
            names.extend(t.strip() for t in tokens if t and t.strip())
        if single and single.strip():
            names.append(single.strip())

        # ---- De-dup helper
        def _dedup_merge(existing: list[str], new_items: list[str]) -> list[str]:
            seen = {n.lower() for n in existing}
            added = []
            for n in new_items:
                k = n.lower()
                if k not in seen:
                    seen.add(k)
                    added.append(n)
            return existing + added

        # A) Add to local list
        if add_btn:
            if names:
                before = len(st.session_state.ingredients)
                st.session_state.ingredients = _dedup_merge(st.session_state.ingredients, names)
                added_count = len(st.session_state.ingredients) - before
                st.success(f"Added {added_count} ingredient{'s' if added_count != 1 else ''}.")
            else:
                st.info("Type one or more ingredient names first.")

        # B) Send to backend (everything we have, including newly typed)
        if api_btn:
            to_send = _dedup_merge(list(st.session_state.ingredients), names)
            if not to_send:
                st.warning("Add at least one ingredient before calling the API.")
            else:
                try:
                    r = requests.post(
                        f"{BACKEND}/api/pocket-chef",
                        json={"user_id": "demo", "ingredients": to_send},
                        timeout=20
                    )
                    r.raise_for_status()
                    data = r.json()  # { recipe: "...", xp_gained: ..., ... }

                    # Show the raw recipe text
                    st.success("Recipe from backend:")
                    st.code(data.get("recipe", ""), language="markdown")

                    # Optional: jump into your step viewer using returned text
                    recipe_text = data.get("recipe", "")
                    lines = [ln.strip() for ln in recipe_text.splitlines() if ln.strip()]
                    steps = [ln for ln in lines if ln.lower().startswith(("1.", "2.", "3.", "4.", "step", "- "))]
                    if not steps and recipe_text:
                        steps = [recipe_text]

                    if steps:
                        dish_name = _parse_dish_name(recipe_text)
                        all_names = set(get_all_recipes().keys())
                        final_name = dish_name
                        i = 2
                        while final_name in all_names:
                            final_name = f"{dish_name} (AI {i})"
                            i += 1

                        st.session_state["ai_recipe"] = {"name": final_name, "steps": steps, "time_min": 20}
                        st.session_state.recipe_key = final_name
                        st.session_state.screen = "recipe"
                        st.rerun()
                except Exception as e:
                    st.error(f"API error: {e}")

    # --- Current list with per-item delete ---
    if st.session_state.ingredients:
        st.markdown("#### Current Ingredients")
        to_delete_index = None

        for i, name in enumerate(st.session_state.ingredients):
            c1, c2 = st.columns([0.82, 0.18], vertical_alignment="center")
            with c1:
                st.markdown(f"{i+1}. **{name}**")
            with c2:
                if st.button("Remove", key=f"del_{scope}_{i}_{_keyify(name)}"):
                    to_delete_index = i

        # Apply deletion after the loop (safer for Streamlit)
        if to_delete_index is not None:
            del st.session_state.ingredients[to_delete_index]
            try:
                st.rerun()
            except Exception:
                st.experimental_rerun()

        if st.button("Clear List", key=f"clear_{scope}", type="secondary"):
            st.session_state.ingredients = []
            st.info("Ingredients cleared.")
    else:
        st.caption("No ingredients yet. Add some above.")

def _all_recipes_with_ai() -> Dict[str, Recipe]:
    recipes = get_all_recipes()
    if "ai_recipe" in st.session_state:
        ai = st.session_state["ai_recipe"]
        recipes[ai["name"]] = Recipe(ai["name"], ai["steps"], ai["time_min"])
    return recipes

# ---------- Home ----------
def slug(s: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in s)

def home_screen():
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.markdown("<h2 class='title'>Culinary Quest</h2>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Pick a recipe to begin.</p>", unsafe_allow_html=True)

    pop = getattr(st, "popover", None)
    if pop:
        with pop("Open Command Panel"): command_panel_ui("home")
    else:
        with st.expander("Open Command Panel"): command_panel_ui("home")

    st.divider()

    recipes = get_all_recipes()
    cols = st.columns(3, gap="small")

    for i, key in enumerate(list(recipes.keys())):
        r = recipes[key]
        with cols[i % 3]:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<h4>{r.name}</h4>", unsafe_allow_html=True)
            st.markdown(f"<span class='badge'>{len(r.steps)} steps · ~{r.time_min} min</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            if st.button(f"Start {r.name} ▶", key=f"start_{slug(key)}", use_container_width=True):
                load_recipe(key)
                st.rerun()

# ---------- Recipe ----------
def recipe_screen():
    recipes = get_all_recipes()
    if "ai_recipe" in st.session_state:
        ai = st.session_state["ai_recipe"]
        recipes[ai["name"]] = Recipe(ai["name"], ai["steps"], ai["time_min"])

    key = st.session_state.recipe_key
    if not key or key not in recipes:
        st.warning("No recipe selected yet.")
        go_home()
        st.rerun()
        return
    r = recipes[key]

    with st.container():
        st.markdown("<div class='sticky-top'></div>", unsafe_allow_html=True)
        left, mid, right = st.columns([1, 2, 1], gap="small")
        with left:
            st.button("◀ Prev", key="prev_btn", on_click=prev_step,
                      disabled=(st.session_state.step_idx == 0), use_container_width=True)
        with mid:
            st.markdown(f"<h2 class='title'>{r.name}</h2>", unsafe_allow_html=True)
            st.markdown(f"<p class='subtitle'>Step {st.session_state.step_idx+1} of {len(r.steps)}</p>", unsafe_allow_html=True)
        with right:
            st.button("Next ▶", key="next_btn", on_click=next_step,
                      disabled=(st.session_state.step_idx == len(r.steps)-1), use_container_width=True)

    st.divider()

    idx = st.session_state.step_idx
    svg_html(step_svg(r.name, idx + 1, len(r.steps), r.steps[idx]), height=340)
    st.markdown(f"<div class='steptext'>{r.steps[idx]}</div>", unsafe_allow_html=True)

    c1, _, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("◀ Back to Home", key="back_btn", type="secondary"):
            go_home()
            st.rerun()
    with c3:
        if st.button("Restart Recipe", key="restart_btn", type="secondary"):
            st.session_state.step_idx = 0
            st.toast("Restarted")

# ---------- Router ----------
if st.session_state.screen == "home":
    home_screen()
else:
    recipe_screen()