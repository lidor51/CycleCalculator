import io
import math
import json
import os
from pathlib import Path
import streamlit as st
import pandas as pd
from utils import compute_cycle_summary

st.set_page_config(layout="wide", page_title="FRC Cycles Calculator")

st.title("FRC Cycles Calculator")

# Early cache paths so we can read persisted UI state (dark mode default)
CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)
STATE_PATH = CACHE_DIR / "state.json"
CSV_CACHE_PATH = CACHE_DIR / "actions.csv"
try:
    initial_state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
except Exception:
    initial_state = {}

# Dark mode default: read from cached state, default to True
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = initial_state.get("dark_mode", True)

# Sidebar toggle (keeps state across reruns)
st.sidebar.checkbox("Dark mode", value=st.session_state.get("dark_mode", True), key="dark_mode")

def _apply_theme(dark: bool):
    if dark:
        st.markdown(
            """
            <style>
            /* Titles */
            h1, h2, h3, .stSubheader { color: #ff7a00 !important; }

            /* App background and default text */
            .stApp, .block-container { background-color: #0b1116 !important; color: #e6eef6 !important; }

            /* Inputs / uploader / expander text */
            .stFileUploader, .stNumberInput, .stTextInput, .stSelectbox, .stExpander, .stMarkdown,
            input, textarea, select, input[type="number"], input[type="file"] {
                color: #e6eef6 !important;
                background-color: #071019 !important;
                border-color: #1f2a33 !important;
            }

            /* File uploader (baseweb) */
            div[data-baseweb="file-uploader"] { background-color: #071019 !important; color: #e6eef6 !important; }

            /* Labels and small text */
            label, .stLabel, .css-1kyxreq { color: #ff7a00 !important; }

            /* Buttons styled orange */
            .stButton>button, .stDownloadButton>button { background-color: #ff7a00 !important; color: #0b1116 !important; border: none !important; }

            /* DataFrame table colors */
            .stDataFrame table, .stDataFrame th, .stDataFrame td { background-color: #071019 !important; color: #e6eef6 !important; }

            /* Specific element tweaks */
            .css-1d391kg { background-color: #0b1116 !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <style>
            /* Titles in orange */
            h1, h2, h3, .stSubheader { color: #ff7a00 !important; }

            /* Light background */
            .block-container { background-color: white !important; color: inherit !important; }

            /* Buttons styled orange on light theme */
            .stButton>button, .stDownloadButton>button { background-color: #ff7a00 !important; color: white !important; border: none !important; }

            /* Ensure dataframes use light styling */
            .stDataFrame table, .stDataFrame th, .stDataFrame td { background-color: white !important; color: inherit !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )

_apply_theme(st.session_state.get("dark_mode", False))

# Safe rerun for both old and new Streamlit versions
def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        try:
            st.experimental_rerun()
        except Exception:
            pass  # silently ignore if neither works

# (no explicit rerun helper — Streamlit buttons trigger a rerun automatically)
# Cache paths
CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)
STATE_PATH = CACHE_DIR / "state.json"
CSV_CACHE_PATH = CACHE_DIR / "actions.csv"

def load_state_file():
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_state_file(state: dict, csv_bytes: bytes = None):
    try:
        # ensure dark_mode persists when saving state
        if "dark_mode" in st.session_state and "dark_mode" not in state:
            state["dark_mode"] = st.session_state.get("dark_mode")
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        if csv_bytes is None and "_last_csv" in st.session_state:
            csv_bytes = st.session_state.get("_last_csv")
        if csv_bytes is not None:
            try:
                CSV_CACHE_PATH.write_bytes(csv_bytes)
            except Exception:
                # fallback: write string CSV from df if available
                try:
                    df.to_csv(CSV_CACHE_PATH, index=False, header=False, encoding=state.get("encoding", "utf-8"))
                except Exception:
                    pass
    except Exception:
        pass

# Read uploaded bytes or cached CSV
uploader = st.file_uploader("Upload actions CSV (columns: name,duration_sec,qual_pts,playoff_pts,probability)", type=["csv"]) 
content = None
state_data = load_state_file()
if uploader is not None:
    content = uploader.read()
    st.session_state["_last_csv"] = content
else:
    if CSV_CACHE_PATH.exists():
        try:
            content = CSV_CACHE_PATH.read_bytes()
            st.session_state["_last_csv"] = content
        except Exception:
            content = None

if content is None:
    st.info("Upload a CSV or save one to .cache to get started. Columns are read by order, not name.")
    st.stop()

# Read bytes and try common encodings (Hebrew often uses cp1255/windows-1255)
encodings_to_try = ["utf-8", "cp1255", "windows-1255", "iso-8859-8", "cp1252", "latin1"]
df = None
used_encoding = None
for enc in encodings_to_try:
    try:
        text = content.decode(enc)
        df = pd.read_csv(io.StringIO(text), header=None)
        used_encoding = enc
        break
    except Exception:
        continue

if df is None:
    st.error("Could not auto-detect encoding. Choose one manually below.")
    enc_choice = st.selectbox("Pick encoding to decode CSV", encodings_to_try, index=1)
    try:
        text = content.decode(enc_choice, errors="replace")
        df = pd.read_csv(io.StringIO(text), header=None)
        used_encoding = enc_choice
    except Exception as e:
        st.error(f"Failed to parse CSV with encoding {enc_choice}: {e}")
        st.stop()

df = df.iloc[:, :5]
# If first row appears to be a header (non-numeric duration), drop it
try:
    # try parsing the duration in the first row
    _ = float(df.iat[0, 1])
except Exception:
    df = df.drop(index=0).reset_index(drop=True)
df = df.iloc[:, :5]
df.columns = ["name", "duration", "qual_pts", "playoff_pts", "prob"]
df["duration"] = pd.to_numeric(df["duration"], errors="coerce").fillna(0.0)
df["qual_pts"] = pd.to_numeric(df["qual_pts"], errors="coerce").fillna(0.0)
df["playoff_pts"] = pd.to_numeric(df["playoff_pts"], errors="coerce").fillna(0.0)
df["prob"] = pd.to_numeric(df["prob"], errors="coerce").fillna(0.0)

# Restore cycles and global_time from state_data if present
if "cycles" not in st.session_state:
    st.session_state.cycles = state_data.get("cycles", []) if state_data else []

default_global = state_data.get("global_time", 135.0) if state_data else 135.0

st.subheader("Actions (indexed)")
df_display = df.copy()
df_display.index = df_display.index.astype(str)
st.dataframe(df_display.style.format({"duration":"{:.2f}", "prob":"{:.4f}"}), use_container_width=True)

def _on_global_time_change():
    # called when global_time changes
    save_state_file({"cycles": st.session_state.get("cycles", []), "global_time": st.session_state.get("global_time", default_global), "encoding": used_encoding}, csv_bytes=st.session_state.get("_last_csv"))

global_time = st.number_input("Global time (sec)", min_value=1.0, value=float(default_global), step=1.0, key="global_time", on_change=_on_global_time_change)



# Sidebar cache controls
with st.sidebar.expander("Cache"):
    st.write(f"Cached CSV: {'yes' if CSV_CACHE_PATH.exists() else 'no'}")
    st.write(f"Cached state: {'yes' if STATE_PATH.exists() else 'no'}")

    if st.button("Save state now"):
        try:
            save_state_file({"cycles": st.session_state.get("cycles", []), "global_time": st.session_state.get("global_time", default_global), "encoding": used_encoding}, csv_bytes=st.session_state.get("_last_csv"))
            st.success("State and CSV saved to .cache")
        except Exception as e:
            st.error(f"Failed to save state: {e}")

    if st.button("Reload cached CSV/state"):
        try:
            st.experimental_rerun()
        except Exception:
            st.info("Please refresh the browser to reload the cached CSV/state.")

    if st.button("Clear cache"):
        try:
            if CSV_CACHE_PATH.exists():
                CSV_CACHE_PATH.unlink()
            if STATE_PATH.exists():
                STATE_PATH.unlink()
        except Exception:
            pass
        st.session_state.cycles = []
        st.success("Cache cleared")
        try:
            st.experimental_rerun()
        except Exception:
            st.info("Please refresh the browser to reload the app.")

if "cycles" not in st.session_state:
    st.session_state.cycles = []

# Clear editing state if save/cancel just happened (before widgets render)
if st.session_state.get("_just_finished_editing"):
    st.session_state["editing_idx"] = None
    st.session_state["new_cycle_name"] = ""
    st.session_state["current_sequence"] = []
    st.session_state["_just_finished_editing"] = False
    # collapse the add/edit expander after finishing an edit
    st.session_state.setdefault("add_cycle_expander", False)

st.subheader("Defined Cycles")
remove_idx = None
edit_idx = None
move_up_idx = None
move_down_idx = None
for idx, c in enumerate(st.session_state.cycles):
    cols = st.columns([0.5, 7, 1, 1, 1, 1])
    cols[0].write(idx)
    try:
        action_names = df.loc[c["actions"], "name"].tolist()
    except Exception:
        action_names = []
    cols[1].markdown(f"**{c['name']}** — " + " → ".join(action_names))
    if cols[2].button("Edit", key=f"edit_{idx}"):
        st.session_state["editing_idx"] = idx
        st.session_state["new_cycle_name"] = st.session_state.cycles[idx]["name"]
        st.session_state["current_sequence"] = list(st.session_state.cycles[idx]["actions"])
        st.session_state["add_cycle_expander"] = True
        safe_rerun()
    if cols[3].button("↑", key=f"up_{idx}"):
        if idx > 0:
            st.session_state.cycles[idx-1], st.session_state.cycles[idx] = st.session_state.cycles[idx], st.session_state.cycles[idx-1]
            save_state_file({"cycles": st.session_state.get("cycles", []), "global_time": st.session_state.get("global_time", default_global), "encoding": used_encoding}, csv_bytes=st.session_state.get("_last_csv"))
            safe_rerun()
    if cols[4].button("↓", key=f"down_{idx}"):
        if idx < len(st.session_state.cycles)-1:
            st.session_state.cycles[idx+1], st.session_state.cycles[idx] = st.session_state.cycles[idx], st.session_state.cycles[idx+1]
            save_state_file({"cycles": st.session_state.get("cycles", []), "global_time": st.session_state.get("global_time", default_global), "encoding": used_encoding}, csv_bytes=st.session_state.get("_last_csv"))
            safe_rerun()
    if cols[5].button("Remove", key=f"del_{idx}"):
        st.session_state.cycles.pop(idx)
        save_state_file({"cycles": st.session_state.get("cycles", []), "global_time": st.session_state.get("global_time", default_global), "encoding": used_encoding}, csv_bytes=st.session_state.get("_last_csv"))
        safe_rerun()

with st.expander("Add new cycle", expanded=st.session_state.get("add_cycle_expander", False)):
    # prefill name if editing
    c_name_prefill = st.session_state.get("new_cycle_name", "")
    c_name = st.text_input("Cycle name", key="new_cycle_name", value=c_name_prefill)
    raw_options = [f"{i} — {n}" for i, n in zip(df.index, df["name"]) ]
    placeholder = "-- select action --"
    options = [placeholder] + raw_options

    if "current_sequence" not in st.session_state:
        st.session_state.current_sequence = []
    
    # use a dynamic key that changes each time we add an action to reset selectbox
    if "action_select_key" not in st.session_state:
        st.session_state.action_select_key = 0

    def _on_action_select():
        current_key = f"select_action_to_add_{st.session_state.action_select_key}"
        action_choice = st.session_state.get(current_key)
        if action_choice and action_choice != placeholder:
            try:
                idx = int(action_choice.split(" — ")[0])
                st.session_state.current_sequence.append(idx)
                st.session_state.action_select_key += 1
            except Exception:
                pass

    st.markdown("**Pick an action to append:**")
    action_choice = st.selectbox("Action to add", options, key=f"select_action_to_add_{st.session_state.action_select_key}", on_change=_on_action_select)

    st.markdown("**Current sequence (preview):**")
    try:
        seq_names = df.loc[st.session_state.current_sequence, 'name'].tolist() if st.session_state.current_sequence else []
    except Exception:
        seq_names = []
    st.write(" → ".join(seq_names) if seq_names else "(empty)")

    cola, colb, colc = st.columns([1,1,1])
    if cola.button("Remove last from sequence", key="remove_last_seq"):
        if st.session_state.current_sequence:
            st.session_state.current_sequence.pop()
            safe_rerun()
    if colb.button("Clear sequence", key="clear_seq"):
        st.session_state.current_sequence = []
        safe_rerun()

    if st.session_state.get("editing_idx") is not None:
        if colc.button("Save changes", key="save_cycle_btn"):
            if not c_name:
                st.error("Cycle needs a name")
            elif not st.session_state.current_sequence:
                st.error("Sequence is empty — add actions first")
            else:
                i = st.session_state.get("editing_idx")
                st.session_state.cycles[i] = {"name": c_name, "actions": list(st.session_state.current_sequence)}
                save_state_file({"cycles": st.session_state.get("cycles", []), "global_time": st.session_state.get("global_time", default_global), "encoding": used_encoding}, csv_bytes=st.session_state.get("_last_csv"))
                st.success(f"Saved changes to cycle '{c_name}'")
                st.session_state["_just_finished_editing"] = True
                st.session_state["add_cycle_expander"] = False
                safe_rerun()
        if cola.button("Cancel edit", key="cancel_edit_btn"):
            st.session_state["_just_finished_editing"] = True
            st.session_state["add_cycle_expander"] = False
            safe_rerun()
    else:
        if colc.button("Add cycle", key="add_cycle_btn"):
            if not c_name:
                st.error("Cycle needs a name")
            elif not st.session_state.current_sequence:
                st.error("Sequence is empty — add actions first")
            else:
                st.session_state.cycles.append({"name": c_name, "actions": list(st.session_state.current_sequence)})
                # persist state after adding
                save_state_file({"cycles": st.session_state.get("cycles", []), "global_time": st.session_state.get("global_time", default_global), "encoding": used_encoding}, csv_bytes=st.session_state.get("_last_csv"))
                st.success(f"Added cycle '{c_name}'")
                st.session_state.current_sequence = []
                st.session_state["add_cycle_expander"] = False
                safe_rerun()
                safe_rerun()

summaries = []
for c in st.session_state.cycles:
    summaries.append(compute_cycle_summary(df, c["name"], c["actions"], global_time))

if summaries:
    summary_df = pd.DataFrame(summaries)
    # Display formatting
    fmt = {
        "Cycle time": "{:.2f}",
        "Qualification Pts": "{:.2f}",
        "Playoff Pts": "{:.2f}",
        "Probability": "{:.4f}",
        "Total cycles": "{:.0f}",
        "Total Qualification Score": "{:.2f}",
        "Estimated Qualification Score": "{:.2f}",
        "Total Playoffs Score": "{:.2f}",
        "Estimated Playoffs Score": "{:.2f}",
        "Pts-per-sec": "{:.4f}",
        "Estimated Pts-per-sec": "{:.4f}"
    }
    st.subheader("Summary")
    st.dataframe(summary_df.style.format(fmt), use_container_width=True)

    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="cycles")
        df.to_excel(writer, index=False, sheet_name="actions")
    towrite.seek(0)
    st.download_button("Download Excel", data=towrite, file_name="cycles_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

else:
    st.info("No cycles defined yet. Add a cycle in the expander above.")
