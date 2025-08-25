import streamlit as st
import json
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import shlex
import random
import os
import requests

st.set_page_config(page_title="Budgeter", layout="wide")
BACKEND = "http://127.0.0.1:5000"

DATA_FILE = Path("pages/budgeter_state.json")
GOAL_FILE = Path("pages/budgeter_goal.json")
SETTINGS_FILE = Path("pages/budgeter_settings.json")
TRANSACTIONS_FILE = Path("pages/budgeter_transactions.jsonl")
THEME_FILE = Path("pages/budgeter_theme.json")

PRESET_THEMES = {"Light": {"bg": "#ffffff", "text": "#0f172a"}, "Soft Gray": {"bg": "#f3f4f6", "text": "#111827"}, "Dark": {"bg": "#0f172a", "text": "#f8fafc"}, "Midnight": {"bg": "#0b1220", "text": "#e2e8f0"}, "Ocean": {"bg": "#06283D", "text": "#E3F6FF"}, "Forest": {"bg": "#0f2d1d", "text": "#e6ffed"}, "Plum": {"bg": "#2d1436", "text": "#f5e9ff"}, "Sepia": {"bg": "#f9f1e7", "text": "#4a3428"}, "Solarized Light": {"bg": "#fdf6e3", "text": "#073642"}, "Solarized Dark": {"bg": "#002b36", "text": "#eee8d5"}, "High Contrast": {"bg": "#000000", "text": "#ffffff"}, "Night Owl": {"bg": "#011627", "text": "#d6deeb"}, "Sand": {"bg": "#f7f3e9", "text": "#2d2a26"},}
DEFAULT_THEME = PRESET_THEMES["Light"]

def _normalize_name(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())

def _match_preset(name: str):
    key = _normalize_name(name)
    for preset in PRESET_THEMES.keys():
        if _normalize_name(preset) == key:
            return preset
    return None

def load_theme():
    if THEME_FILE.exists():
        try:
            data = json.loads(THEME_FILE.read_text())
            bg = str(data.get("bg", DEFAULT_THEME["bg"]))
            text = str(data.get("text", DEFAULT_THEME["text"]))
            return bg, text
        except Exception:
            pass
    return DEFAULT_THEME["bg"], DEFAULT_THEME["text"]

def save_theme(bg: str, text: str):
    THEME_FILE.parent.mkdir(parents=True, exist_ok=True)
    THEME_FILE.write_text(json.dumps({"bg": bg, "text": text}, indent=2))

def _hex_to_rgb(hex_str: str):
    s = hex_str.lstrip("#")
    if len(s) == 3:
        s = "".join(c*2 for c in s)
    return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))

def _is_dark(hex_str: str) -> bool:
    r, g, b = _hex_to_rgb(hex_str)
    return (0.299*r + 0.587*g + 0.114*b) < 140

def apply_theme_css(bg: str, text: str):
    dark_ui = _is_dark(bg)

    if dark_ui:
        btn_bg       = "#e5e7eb"
        btn_bg_hover = "#d1d5db"
        btn_fg       = "#111827"
        btn_border   = "#cbd5e1"
    else:
        btn_bg       = "#334155"
        btn_bg_hover = "#1f2937"
        btn_fg       = "#ffffff"
        btn_border   = "#334155"

    st.markdown(
        f"""
        <style>
        :root
        {{
          --budgeter-bg: {bg};
          --budgeter-text: {text};
          --btn-bg: {btn_bg};
          --btn-bg-hover: {btn_bg_hover};
          --btn-fg: {btn_fg};
          --btn-border: {btn_border};
        }}

        .stApp
        {{
          background-color: var(--budgeter-bg) !important;
          color: var(--budgeter-text) !important;
        }}
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        .stMarkdown, .stText, label,
        div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"]
        {{
          color: var(--budgeter-text) !important;
        }}

        input, textarea, select
        {{
          color: #111827 !important;
        }}

        .stButton > button,
        .stDownloadButton > button,
        .stFormSubmitButton > button,
        button[kind],
        div[data-testid="baseButton-secondary"] > button,
        div[data-testid="baseButton-primary"] > button
        {{
          background-color: var(--btn-bg) !important;
          color: var(--btn-fg) !important;
          border: 1px solid var(--btn-border) !important;
          box-shadow: none !important;
        }}
        .stButton > button * ,
        .stDownloadButton > button * ,
        .stFormSubmitButton > button * ,
        button[kind] * ,
        div[data-testid="baseButton-secondary"] > button * ,
        div[data-testid="baseButton-primary"] > button *
        {{
          color: var(--btn-fg) !important;
          fill: currentColor !important;
        }}
        .stButton > button:hover,
        .stDownloadButton > button:hover,
        .stFormSubmitButton > button:hover,
        button[kind]:hover,
        div[data-testid="baseButton-secondary"] > button:hover,
        div[data-testid="baseButton-primary"] > button:hover
        {{
          background-color: var(--btn-bg-hover) !important;
          border-color: var(--btn-bg-hover) !important;
          color: var(--btn-fg) !important;
        }}
        .stButton > button:disabled,
        .stDownloadButton > button:disabled,
        .stFormSubmitButton > button:disabled {{
          background-color: var(--btn-bg) !important;
          color: var(--btn-fg) !important;
          opacity: 0.6 !important; /* readable but muted */
        }}

        .stCaption, .stTooltipContent {{ color: var(--budgeter-text) !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    plt.rcParams.update({"text.color": text, "axes.labelcolor": text, "xtick.color": text, "ytick.color": text,})

def load_goal():
    if GOAL_FILE.exists():
        try:
            data = json.loads(GOAL_FILE.read_text())
            return str(data.get("goal_name", "My Goal")), float(data.get("goal_amount", 0.0))
        except Exception:
            pass
    return "My Goal", 0.0

def save_goal():
    GOAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    GOAL_FILE.write_text(json.dumps({"goal_name": st.session_state.savingsGoalName, "goal_amount": st.session_state.savingsGoalAmount}, indent=2))

def delete_goal():
    try:
        GOAL_FILE.unlink()
    except FileNotFoundError:
        pass

def load_persisted():
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text())
            return float(data.get("account", 0.0)), float(data.get("savings", 0.0))
        except Exception:
            pass
    return 0.0, 0.0

def save_persisted():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps({"account": st.session_state.amountInAccount, "savings": st.session_state.amountInSavings}, indent=2))

def load_settings():
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text())
            return float(data.get("auto_save_percent", 0.0))
        except Exception:
            pass
    return 0.0

def save_settings():
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps({"auto_save_percent": st.session_state.autoSavePercent}, indent=2))

def log_txn(kind: str, amount: float, note: str = ""):
    if amount <= 0:
        return
    TRANSACTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": datetime.now().isoformat(), "type": kind, "amount": float(amount)}
    if note:
        rec["note"] = str(note)
    with TRANSACTIONS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")

def load_txns():
    txns = []
    if TRANSACTIONS_FILE.exists():
        for line in TRANSACTIONS_FILE.read_text().splitlines():
            try:
                txns.append(json.loads(line))
            except Exception:
                continue
    return txns

def rewrite_txns(txns):
    TRANSACTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with TRANSACTIONS_FILE.open("w", encoding="utf-8") as f:
        for r in txns:
            f.write(json.dumps(r) + "\n")

def filter_txns(txns, since_dt=None):
    out = []
    for r in txns:
        try:
            dt = datetime.fromisoformat(r["ts"])
        except Exception:
            continue
        if since_dt is None or dt >= since_dt:
            out.append(r)
    return out

def totals_from_txns(txns):
    totals = {"Added": 0.0, "Spent": 0.0, "Saved": 0.0, "Moved Back": 0.0}
    for r in txns:
        t = r.get("type")
        a = float(r.get("amount", 0.0))
        if t == "add":
            totals["Added"] += a
        elif t == "spend":
            totals["Spent"] += a
        elif t in ("move_to_savings", "auto_move_to_savings"):
            totals["Saved"] += a
        elif t == "move_to_account":
            totals["Moved Back"] += a
    return totals

def undo_last_txn():
    txns = load_txns()
    if not txns:
        st.warning("No transactions to undo.")
        return False
    last = txns.pop()
    t = last.get("type")
    amt = float(last.get("amount", 0.0))
    if t == "add":
        st.session_state.amountInAccount -= amt
    elif t == "spend":
        st.session_state.amountInAccount += amt
    elif t in ("move_to_savings", "auto_move_to_savings"):
        st.session_state.amountInSavings -= amt
        st.session_state.amountInAccount += amt
    elif t == "move_to_account":
        st.session_state.amountInAccount -= amt
        st.session_state.amountInSavings += amt
    else:
        txns.append(last)
        st.error("Cannot undo this transaction type.")
        return False
    save_persisted()
    rewrite_txns(txns)
    st.success(f"Undid last transaction: {t} ${amt:,.2f}")
    return True

def composition_pie_small(account_bal, savings_bal, spent_total, title="Composition"):
    total = account_bal + savings_bal + spent_total
    if total <= 0:
        st.info("No funds or transactions yet.")
        return
    labels = ["In Account", "In Savings", "Spent"]
    values = [account_bal, savings_bal, spent_total]
    colors = ["#2b6cb0", "#ed8936", "#38a169"]  # blue, orange, green

    fig, ax = plt.subplots(figsize=(4, 4))
    wedges, _ = ax.pie(values, colors=colors, startangle=90, wedgeprops=dict(linewidth=1, edgecolor="white"))
    ax.axis("equal")

    pct = [v / total * 100 for v in values]
    legend_labels = [f"{labels[i]} — ${values[i]:,.0f} ({pct[i]:.0f}%)" for i in range(3)]
    ax.legend(wedges, legend_labels, loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=1, frameon=False)
    fig.tight_layout()
    st.pyplot(fig)

def _range_from_token(tok: str):
    tok = tok.lower()
    if tok in ("24h", "day", "daily"): return timedelta(days=1)
    if tok in ("week", "weekly", "wk"): return timedelta(days=7)
    if tok in ("month", "monthly", "mo"): return timedelta(days=30)
    if tok in ("year", "yearly", "yr"): return timedelta(days=365)
    if tok in ("5y", "5yr", "5yrs", "5years"): return timedelta(days=365*5)
    if tok in ("life", "lifetime", "all"): return None
    return None

def handle_command(cmd_str: str):
    try:
        parts = shlex.split(cmd_str)
    except Exception:
        st.error("Couldn't parse command. Try quotes around names, e.g., goal 3000 \"New laptop\".")
        return
    if not parts:
        st.warning("Please enter a command.")
        return
    cmd = parts[0].lower()

    def _to_amount(i=1):
        if len(parts) <= i:
            st.error("Missing amount.")
            return None
        try:
            return float(parts[i].rstrip("%"))
        except Exception:
            st.error("Amount must be a number.")
            return None

    if cmd in ("add", "deposit"):
        amt = _to_amount(1)
        if amt is None or amt <= 0: return
        st.session_state.amountInAccount += amt
        log_txn("add", amt)
        pct = float(st.session_state.autoSavePercent or 0.0)
        pct = max(0.0, min(pct, 100.0))
        auto_move = round(amt * (pct / 100.0), 2)
        if auto_move > 0:
            auto_move = min(auto_move, st.session_state.amountInAccount)
            st.session_state.amountInAccount -= auto_move
            st.session_state.amountInSavings += auto_move
            log_txn("auto_move_to_savings", auto_move)
            st.info(f"Auto-saved {pct:.0f}% (${auto_move:,.2f}) from this deposit.")
        save_persisted()
        st.success(f"Added ${amt:,.2f}. Account: ${st.session_state.amountInAccount:,.2f}")

    elif cmd in ("save", "move", "mv"):
        amt = _to_amount(1)
        if amt is None or amt <= 0: return
        amt = min(amt, st.session_state.amountInAccount)
        if amt <= 0:
            st.warning("No available balance to move."); return
        st.session_state.amountInAccount -= amt
        st.session_state.amountInSavings += amt
        note = " ".join(parts[2:]) if len(parts) > 2 else ""
        log_txn("move_to_savings", amt, note=note)
        save_persisted()
        st.success(f"Saved ${amt:,.2f}.")

    elif cmd in ("spend", "pay"):
        amt = _to_amount(1)
        if amt is None or amt <= 0: return
        amt = min(amt, st.session_state.amountInAccount)
        if amt <= 0:
            st.warning("No available balance to spend."); return
        st.session_state.amountInAccount -= amt
        note = " ".join(parts[2:]) if len(parts) > 2 else ""
        log_txn("spend", amt, note=note)
        save_persisted()
        st.success(f"Spent ${amt:,.2f}.")

    elif cmd in ("back", "return", "withdraw"):
        amt = _to_amount(1)
        if amt is None or amt <= 0: return
        amt = min(amt, st.session_state.amountInSavings)
        if amt <= 0:
            st.warning("No savings available to move back."); return
        st.session_state.amountInAccount += amt
        st.session_state.amountInSavings -= amt
        note = " ".join(parts[2:]) if len(parts) > 2 else ""
        log_txn("move_to_account", amt, note=note)
        save_persisted()
        st.success(f"Moved back ${amt:,.2f} to account.")

    elif cmd == "goal":
        amt = _to_amount(1)
        if amt is None or amt < 0: return
        name = " ".join(parts[2:]) if len(parts) > 2 else st.session_state.savingsGoalName or "My Goal"
        st.session_state.savingsGoalAmount = float(amt)
        st.session_state.savingsGoalName = name
        save_goal()
        st.success(f"Goal set: {name} — ${amt:,.2f}")

    elif cmd == "autosave":
        pct = _to_amount(1)
        if pct is None or pct < 0: return
        pct = max(0.0, min(pct, 100.0))
        st.session_state.autoSavePercent = float(pct)
        save_settings()
        st.success(f"Auto-save set to {pct:.0f}% of each deposit.")

    elif cmd == "theme":
        if len(parts) < 2:
            st.error("Usage: theme THEME_NAME")
            return
        want = " ".join(parts[1:])
        preset = _match_preset(want)
        if not preset:
            st.error("Unknown theme. Available: " + ", ".join(PRESET_THEMES.keys()))
            return
        sel = PRESET_THEMES[preset]
        st.session_state.theme_bg = sel["bg"]
        st.session_state.theme_text = sel["text"]
        save_theme(sel["bg"], sel["text"])
        apply_theme_css(sel["bg"], sel["text"])
        st.success(f"Theme set to “{preset}”.")
        try: st.rerun()
        except Exception: st.experimental_rerun()

    elif cmd in ("delete", "clear", "wipe") and len(parts) >= 2 and parts[1].lower() == "money":
        if len(parts) >= 3 and parts[2].lower() in ("account", "acc", "a"):
            if len(parts) < 4:
                st.error("Usage: delete money account AMOUNT"); return
            amt = _to_amount(3)
            if amt is None or amt <= 0: return
            amt = min(amt, st.session_state.amountInAccount)
            st.session_state.amountInAccount -= amt
            save_persisted()
            st.success(f"Deleted ${amt:,.2f} from Account balance.")
        elif len(parts) >= 3 and parts[2].lower() in ("savings", "sav", "s"):
            if len(parts) < 4:
                st.error("Usage: delete money savings AMOUNT"); return
            amt = _to_amount(3)
            if amt is None or amt <= 0: return
            amt = min(amt, st.session_state.amountInSavings)
            st.session_state.amountInSavings -= amt
            save_persisted()
            st.success(f"Deleted ${amt:,.2f} from Savings balance.")
        elif len(parts) >= 3 and parts[2].lower() in ("all", "both"):
            st.session_state.amountInAccount = 0.0
            st.session_state.amountInSavings = 0.0
            save_persisted()
            st.success("Deleted all money from Account and Savings (history retained).")
        else:
            st.info("Usage:\n- delete money account AMOUNT\n- delete money savings AMOUNT\n- delete money all")

    elif cmd == "report":
        rng = parts[1].lower() if len(parts) > 1 else "month"
        td = _range_from_token(rng)
        since_dt = None if td is None else datetime.now() - td
        txns = filter_txns(load_txns(), since_dt)
        totals = totals_from_txns(txns)
        st.write(f"**Report ({rng})**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Added", f"${totals['Added']:,.2f}")
        c2.metric("Spent", f"${totals['Spent']:,.2f}")
        c3.metric("Saved", f"${totals['Saved']:,.2f}")
        c4.metric("Moved Back", f"${totals['Moved Back']:,.2f}")

    elif cmd == "undo":
        if undo_last_txn():
            try: st.rerun()
            except Exception: st.experimental_rerun()

    elif cmd == "help":
        st.info("Commands:\n- add AMOUNT\n- save AMOUNT [note]\n- spend AMOUNT [note]\n- back AMOUNT [note]\n- goal AMOUNT [\"NAME\"]\n- autosave PERCENT (e.g., 20 or 20%)\n- delete money account AMOUNT | delete money savings AMOUNT | delete money all\n- report [24h|week|month|year|5y|lifetime]\n- theme THEME_NAME  (e.g., theme Dark)\n- undo\n- help")
    else:
        log_path = Path("pages/budgeter_unknown_commands.txt")
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{cmd_str}\n")
        try:
            resp = requests.post(f"{BACKEND}/api/budget-buddy",
                                 json={"user_id": "demo", "command": cmd_str}, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            st.info(f"Feedback: {data.get('advice', '(no advice)')}")
        except Exception as e:
            st.error(f"Could not reach Budget Buddy API: {e}")

if "bootstrapped" not in st.session_state:
    acc, sav = load_persisted()
    st.session_state.amountInAccount = acc
    st.session_state.amountInSavings = sav
    st.session_state.bootstrapped = True

if "settings_bootstrapped" not in st.session_state:
    st.session_state.autoSavePercent = load_settings()
    st.session_state.settings_bootstrapped = True

if "theme_bootstrapped" not in st.session_state:
    bg, text = load_theme()
    st.session_state.theme_bg = bg
    st.session_state.theme_text = text
    st.session_state.theme_bootstrapped = True
apply_theme_css(st.session_state.theme_bg, st.session_state.theme_text)

if "reset_code" not in st.session_state:
    st.session_state.reset_code = str(random.randint(10000, 99999))

st.title("Budgeter")
st.write("Welcome to Budgeter, your monthly budgeting app.")
st.write("You can add money at any time, make transactions, set goals, view progress reports, and transaction history")

if "goal_bootstrapped" not in st.session_state:
    gname, gamount = load_goal()
    st.session_state.savingsGoalName = gname
    st.session_state.savingsGoalAmount = gamount
    st.session_state.goal_bootstrapped = True

main_col, cmd_col = st.columns([7, 3])

with cmd_col:
    with st.container(border=True):
        st.header("Command Panel")
        st.caption("Examples: add 25 • spend 8 coffee • goal 3000 \"New laptop\" • autosave 20% • delete money account 15 • report month • theme Dark • undo • help")

        with st.form("cmd_form", clear_on_submit=True):
            cmd_input = st.text_input("Enter command", placeholder='e.g., add 25 | spend 8 coffee | goal 3000 "New laptop" | autosave 20% | theme Dark')
            run_cmd = st.form_submit_button("Run", use_container_width=True)
            if run_cmd and cmd_input.strip():
                handle_command(cmd_input.strip())

        with st.expander("Command Help"):
            st.markdown(
                """
**Commands**
- `add AMOUNT`
- `save AMOUNT [note]`
- `spend AMOUNT [note]`
- `back AMOUNT [note]`
- `goal AMOUNT "NAME"`
- `autosave PERCENT` (0–100, e.g., `autosave 20` or `autosave 20%`)
- `delete money account AMOUNT` • `delete money savings AMOUNT` • `delete money all`
- `report 24h|week|month|year|5y|lifetime`
- `theme THEME_NAME` — choose one of:
  - Light, Soft Gray, Dark, Midnight, Ocean, Forest, Plum, Sepia, Solarized Light, Solarized Dark, High Contrast, Night Owl, Sand
- `undo`
- `help`
                """
            )

        st.subheader("Appearance")
        current_bg, current_text = st.session_state.theme_bg, st.session_state.theme_text
        preset_names = list(PRESET_THEMES.keys())

        def _find_index():
            for i, name in enumerate(preset_names):
                if PRESET_THEMES[name]["bg"].lower() == current_bg.lower() and PRESET_THEMES[name]["text"].lower() == current_text.lower():
                    return i
            return 0

        preset_choice = st.selectbox("Theme preset", preset_names, index=_find_index())

        with st.form("theme_form", clear_on_submit=False):
            sel = PRESET_THEMES[preset_choice]
            st.caption(f"Background: {sel['bg']}  •  Text: {sel['text']}")
            apply_btn = st.form_submit_button("💾 Save & Apply Theme", use_container_width=True)
            if apply_btn:
                st.session_state.theme_bg = sel["bg"]
                st.session_state.theme_text = sel["text"]
                save_theme(sel["bg"], sel["text"])
                apply_theme_css(sel["bg"], sel["text"])
                st.success(f"Theme “{preset_choice}” saved.")
                try: st.rerun()
                except Exception: st.experimental_rerun()

with main_col:
    st.subheader("Savings Goal")
    if st.session_state.savingsGoalAmount and st.session_state.savingsGoalAmount > 0:
        pct_goal = int(min(st.session_state.amountInSavings / st.session_state.savingsGoalAmount, 1.0) * 100)
        st.progress(pct_goal, text=f"{pct_goal}% of '{st.session_state.savingsGoalName}'")
        st.caption(f"${st.session_state.amountInSavings:,.2f} / ${st.session_state.savingsGoalAmount:,.2f}")
        if pct_goal >= 100:
            st.success("🎉 Goal reached!")
    else:
        st.info("Set a savings goal to see your progress.")

    colAdd, colSavings, colSpent, colSaveToAccount = st.columns(4)

    with colAdd:
        with st.form("add_form", clear_on_submit=True):
            add_amt = st.number_input("Enter amount to add", min_value=0.0, step=1.0, key="add_amount")
            submit_add = st.form_submit_button("💲 Add Money", use_container_width=True)
            if submit_add and add_amt > 0:
                add_amt = float(add_amt)
                st.session_state.amountInAccount += add_amt
                log_txn("add", add_amt)
                pct = float(st.session_state.autoSavePercent or 0.0)
                pct = max(0.0, min(pct, 100.0))
                auto_move = round(add_amt * (pct / 100.0), 2)
                if auto_move > 0:
                    auto_move = min(auto_move, st.session_state.amountInAccount)
                    st.session_state.amountInAccount -= auto_move
                    st.session_state.amountInSavings += auto_move
                    log_txn("auto_move_to_savings", auto_move)
                    st.info(f"Auto-saved {pct:.0f}% (${auto_move:,.2f}) from this deposit.")
                save_persisted()
                st.success(f"Balance: ${st.session_state.amountInAccount:,.2f}")

    with colSavings:
        with st.form("savings_form", clear_on_submit=True):
            move_to_savings_amt = st.number_input("Amount to move to savings", min_value=0.0, max_value=float(st.session_state.amountInAccount), step=1.0, key="move_amount")
            submit_move = st.form_submit_button("🏦 Move Money To Savings", use_container_width=True)
            if submit_move and move_to_savings_amt > 0:
                move_to_savings_amt = float(move_to_savings_amt)
                st.session_state.amountInAccount -= move_to_savings_amt
                st.session_state.amountInSavings += move_to_savings_amt
                log_txn("move_to_savings", move_to_savings_amt)
                save_persisted()
                st.success(f"Moved ${move_to_savings_amt:,.2f} to savings.")

    with colSpent:
        with st.form("spend_form", clear_on_submit=True):
            spend_amt = st.number_input("Record spending", min_value=0.0, max_value=float(st.session_state.amountInAccount), step=1.0, key="spend_amount")
            submit_spend = st.form_submit_button("🧾 Record Spending", use_container_width=True)
            if submit_spend and spend_amt > 0:
                spend_amt = float(spend_amt)
                st.session_state.amountInAccount -= spend_amt
                log_txn("spend", spend_amt)
                save_persisted()
                st.success(f"Spent ${spend_amt:,.2f}")

    with colSaveToAccount:
        with st.form("back_to_account_form", clear_on_submit=True):
            move_to_account_amt = st.number_input("Amount to move back to account", min_value=0.0, max_value=float(st.session_state.amountInSavings), step=1.0, key="move_to_account_amount")
            submit_move_back = st.form_submit_button("📉 Move Money To Account", use_container_width=True)
            if submit_move_back and move_to_account_amt > 0:
                move_to_account_amt = float(move_to_account_amt)
                st.session_state.amountInAccount += move_to_account_amt
                st.session_state.amountInSavings -= move_to_account_amt
                log_txn("move_to_account", move_to_account_amt)
                save_persisted()
                st.success(f"Moved ${move_to_account_amt:,.2f} back to your account.")

    st.subheader("Balances")
    st.metric("Account", f"${st.session_state.amountInAccount:,.2f}")
    st.metric("Savings", f"${st.session_state.amountInSavings:,.2f}")

    st.subheader("Add a Goal")
    with st.form("goal_form", clear_on_submit=False):
        new_goal_name = st.text_input("Goal name", value=st.session_state.savingsGoalName, key="goal_name_input")
        new_goal_amount = st.number_input("Target amount", min_value=0.0, step=1.0, value=float(st.session_state.savingsGoalAmount), key="goal_amount_input")
        submit_goal = st.form_submit_button("💾 Save Goal", use_container_width=True)
        if submit_goal:
            st.session_state.savingsGoalName = new_goal_name
            st.session_state.savingsGoalAmount = float(new_goal_amount)
            save_goal()
            st.success("Savings goal saved.")

    remove_goal = st.button("🗑️ Remove Goal", help="Delete your current savings goal")
    if remove_goal:
        st.session_state.savingsGoalName = "My Goal"
        st.session_state.savingsGoalAmount = 0.0
        delete_goal()
        st.success("Savings goal removed.")
        try: st.rerun()
        except Exception: st.experimental_rerun()

    st.subheader("Auto-Save")
    with st.form("autosave_form", clear_on_submit=False):
        auto_pct_input = st.number_input("Automatically move this PERCENT of each deposit to savings", min_value=0.0, max_value=100.0, step=1.0, value=float(st.session_state.autoSavePercent))
        submit_auto = st.form_submit_button("💾 Save Auto-Save %", use_container_width=True)
        if submit_auto:
            st.session_state.autoSavePercent = float(max(0.0, min(auto_pct_input, 100.0)))
            save_settings()
            st.success(f"Auto-save set to {st.session_state.autoSavePercent:.0f}% of each deposit.")

    st.subheader("Reports")
    range_choice = st.selectbox("Choose time range", ("Last 24 hours", "Last week", "Last month", "Last year", "Last 5 years", "Lifetime"), index=2)

    now = datetime.now()
    delta_map = {"Last 24 hours": timedelta(days=1), "Last week": timedelta(days=7), "Last month": timedelta(days=30), "Last year": timedelta(days=365), "Last 5 years": timedelta(days=365*5), "Lifetime": None}
    since = None if delta_map[range_choice] is None else now - delta_map[range_choice]

    all_txns = load_txns()
    sel_txns = filter_txns(all_txns, since)

    if not sel_txns:
        st.info("No transactions found for this range yet.")
    else:
        totals = totals_from_txns(sel_txns)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Added", f"${totals['Added']:,.2f}")
        c2.metric("Spent", f"${totals['Spent']:,.2f}")
        c3.metric("Saved", f"${totals['Saved']:,.2f}")
        c4.metric("Moved Back", f"${totals['Moved Back']:,.2f}")

    st.subheader("Money Composition")
    spent_total = sum(float(t.get("amount", 0.0)) for t in all_txns if t.get("type") == "spend")
    composition_pie_small(account_bal=float(st.session_state.amountInAccount), savings_bal=float(st.session_state.amountInSavings), spent_total=spent_total, title="Account vs Savings vs Spent")

    with st.expander("Advanced"):
        if st.button("RESET ALL BALANCE RELATED DATA (Settings Saved)", use_container_width=True):
            for f in [DATA_FILE, GOAL_FILE, SETTINGS_FILE, TRANSACTIONS_FILE]:
                try:
                    os.remove(f)
                except FileNotFoundError:
                    pass
            st.session_state.amountInAccount = 0.0
            st.session_state.amountInSavings = 0.0
            save_persisted()
            st.success("Data wiped.")
            try:
                st.rerun()
            except Exception:
                st.experimental_rerun()

    with st.expander("🔥 Danger Zone — Reset ALL Data"):
        st.error("This will permanently delete ALL balances, goal, settings, and your entire transaction history. This cannot be undone.")
        c1, c2 = st.columns(2)
        with c1:
            confirm1 = st.checkbox("I understand this will delete **everything** permanently.")
            confirm2 = st.checkbox("I have exported anything I need.")
        with c2:
            phrase = st.text_input("Type EXACTLY:", value="", placeholder='DELETE EVERYTHING')
            code_shown = st.session_state.reset_code
            code_typed = st.text_input(f"Enter unlock code: {code_shown}", value="")
            slider = st.slider("Slide to 100 to unlock", 0, 100, 0)

        can_wipe = confirm1 and confirm2 and phrase.strip() == "DELETE EVERYTHING" and code_typed.strip() == code_shown and slider == 100

        if can_wipe:
            if st.button("🚨 PERMANENTLY DELETE ALL DATA", use_container_width=True):
                for f in [DATA_FILE, GOAL_FILE, SETTINGS_FILE, TRANSACTIONS_FILE, THEME_FILE]:
                    try:
                        os.remove(f)
                    except FileNotFoundError:
                        pass
                st.session_state.amountInAccount = 0.0
                st.session_state.amountInSavings = 0.0
                st.session_state.savingsGoalName = "My Goal"
                st.session_state.savingsGoalAmount = 0.0
                st.session_state.autoSavePercent = 0.0
                st.session_state.theme_bg = DEFAULT_THEME["bg"]
                st.session_state.theme_text = DEFAULT_THEME["text"]
                save_persisted()
                st.success("All data wiped.")
                try:
                    st.rerun()
                except Exception:
                    st.experimental_rerun()
        else:
            st.info("Complete **all** confirmations to enable the delete button.")
