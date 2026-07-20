"""PlainLabs UI — upload a report, get a brief, then chat about it.

Run: uv run streamlit run app.py
"""
import tempfile
from collections import Counter
from pathlib import Path

import streamlit as st

from plainlabs.bootstrap import ensure_ollama, warm
from plainlabs.config import DISCLAIMER, SLM_MODEL
from plainlabs.graph import analyze
from plainlabs.skills.chat import chat_answer
from plainlabs.skills.profile import extract_profile_facts, merge_profile

st.set_page_config(page_title="PlainLabs", page_icon="🩺", layout="centered")

# Bring up Ollama + MedGemma automatically, once per session.
if not st.session_state.get("ollama_ready"):
    with st.spinner(f"Starting Ollama and loading {SLM_MODEL} (first launch is slow)…"):
        ok, msg = ensure_ollama()
        if ok:
            warm()
            st.session_state.ollama_ready = True
        else:
            st.error(msg)
            st.stop()

_STATUS_UI = {  # status -> (streamlit box, emoji)
    "critical": (st.error, "🚨"),
    "abnormal": (st.warning, "🔶"),
    "uncertain": (st.info, "❓"),
    "borderline": (st.info, "🔷"),
    "normal": (st.success, "✅"),
}
_ORDER = {"critical": 0, "abnormal": 1, "uncertain": 2, "borderline": 3, "normal": 4}

# --- session state ---
for key, default in [("findings", None), ("unknown", []), ("history", []), ("profile", [])]:
    st.session_state.setdefault(key, default)

st.title("🩺 PlainLabs")
st.caption("Understand your lab report in plain language. Runs locally · not a diagnosis.")

# --- sidebar: session memory ---
with st.sidebar:
    st.caption(f"🟢 Ollama running · {SLM_MODEL}")
    st.subheader("What I know about you")
    if st.session_state.profile:
        for fact in st.session_state.profile:
            st.write(f"• {fact}")
    else:
        st.caption("Tell me about yourself in the chat (age, diet, symptoms…) and I'll remember it here.")
    if st.button("Clear session"):
        st.session_state.clear()
        st.rerun()

# --- upload + analyse ---
file = st.file_uploader("Upload a lab report", type=["pdf", "png", "jpg", "jpeg", "txt"])
if file and st.button("Explain my report", type="primary"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.name).suffix) as tmp:
        tmp.write(file.getbuffer())
        tmp_path = tmp.name
    with st.spinner("Reading and checking your report…"):
        result = analyze(tmp_path)
    st.session_state.findings = result["findings"]
    st.session_state.unknown = result["unknown"]
    st.session_state.history = []
    Path(tmp_path).unlink(missing_ok=True)

# --- brief + report card ---
if st.session_state.findings is not None:
    findings = sorted(st.session_state.findings, key=lambda f: _ORDER.get(f["status"], 9))
    counts = Counter(f["status"] for f in findings)

    st.subheader("In brief")
    parts = [f"{counts[s]} {s}" for s in _ORDER if counts.get(s)]
    brief = f"Found {len(findings)} values — " + ", ".join(parts) + "."
    (st.error if counts.get("critical") else st.info)(brief)

    st.subheader("Your results")
    for f in findings:
        box, emoji = _STATUS_UI.get(f["status"], (st.info, "•"))
        box(f"{emoji} **{f['name']}: {f['value']} {f['unit']}** — {f['status'].upper()}\n\n{f['explanation']}")

    if st.session_state.unknown:
        st.caption("Not in our reference set (ask your doctor): " + ", ".join(st.session_state.unknown))

    st.divider()

    # --- chat ---
    st.subheader("Ask about your report")
    for q, a in st.session_state.history:
        st.chat_message("user").write(q)
        st.chat_message("assistant").write(a)

    if question := st.chat_input("e.g. why is my HbA1c borderline? (I'm 34, vegetarian…)"):
        st.chat_message("user").write(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                facts = extract_profile_facts(question)
                if facts:
                    st.session_state.profile = merge_profile(st.session_state.profile, facts)
                answer = chat_answer(
                    question, st.session_state.findings,
                    st.session_state.profile, st.session_state.history,
                )
                st.write(answer)
        st.session_state.history.append((question, answer))
        st.rerun()

    st.caption(DISCLAIMER)
else:
    st.info("Upload a lab report above to get started. A sample is in `evals/samples/`.")
