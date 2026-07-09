"""
Borger Hjælp — Streamlit chat frontend (Groq-only version, colorful theme).

Run with:
    streamlit run app.py

Requires a .env file (see .env.example) with:
    GROQ_API_KEY=your_groq_api_key_here
    GROQ_MODEL=llama-3.3-70b-versatile
"""

import os

import streamlit as st
from dotenv import load_dotenv

from llm_client import explain_results, extract_profile
from matching_engine import evaluate_all
from models import CitizenProfile
from schemes import SCHEMES

load_dotenv()

st.set_page_config(page_title="Borger Hjælp", page_icon="🇩🇰", layout="centered")

# ---------------------------------------------------------------------------
# Custom CSS — colorful theme (Danish red/white palette + friendly accents)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #FFF8F6 0%, #FFFFFF 40%);
    }

    /* Hero banner */
    .bh-hero {
        background: linear-gradient(135deg, #C8102E 0%, #E84A5F 60%, #FF8C69 100%);
        padding: 2rem 2rem 1.6rem 2rem;
        border-radius: 18px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 24px rgba(200, 16, 46, 0.25);
    }
    .bh-hero h1 {
        color: white !important;
        font-size: 2.4rem;
        margin-bottom: 0.2rem;
    }
    .bh-hero p {
        color: #FFE8E4;
        font-size: 1.05rem;
        margin: 0;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFF3F0 0%, #FFFFFF 100%);
        border-right: 2px solid #FFD6CE;
    }
    section[data-testid="stSidebar"] h1 {
        color: #C8102E !important;
    }
    section[data-testid="stSidebar"] h3 {
        color: #C8102E !important;
    }

    /* Chat bubbles */
    div[data-testid="stChatMessage"] {
        border-radius: 16px;
        padding: 0.4rem 0.2rem;
        margin-bottom: 0.5rem;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #C8102E, #FF6B6B);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        transition: transform 0.15s ease;
    }
    .stButton > button:hover {
        transform: scale(1.03);
        color: white;
    }

    /* Badges for eligibility status */
    .badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-left: 6px;
    }
    .badge-eligible { background: #D7F5DE; color: #1B7A3D; }
    .badge-needs-info { background: #FFF2CC; color: #9A7B00; }
    .badge-not-eligible { background: #F5D7D7; color: #A31D1D; }

    .scheme-card {
        background: white;
        border: 1px solid #FFE0DA;
        border-radius: 14px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.7rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar: Groq key input + profile inspector
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🇩🇰 Borger Hjælp")
    st.caption("AI agent for navigating Danish public welfare services")

    st.divider()
    st.markdown("### 📋 What we know about you")
    if "profile" in st.session_state:
        known = st.session_state.profile.known_fields()
        if known:
            for field in known:
                st.write(f"✅ {field.replace('_', ' ')}")
        else:
            st.caption("Nothing yet — start chatting below.")
        with st.expander("Raw profile JSON"):
            st.json(st.session_state.profile.model_dump())

    st.divider()
    if st.button("🔄 Reset conversation", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.divider()
    st.caption(
        "⚠️ Disclaimer: this is a student/demo project. Scheme thresholds shown are "
        "illustrative, not verified current legal figures. Always confirm on borger.dk "
        "or with your municipality (kommune) before relying on this for a real decision."
    )

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "profile" not in st.session_state:
    st.session_state.profile = CitizenProfile()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hej! 👋 I'm Borger Hjælp. Tell me a bit about your situation — for example "
                "your age, whether you're a student, your job status, if you have children, "
                "or how long you've lived in Denmark — and I'll tell you which Danish public "
                "benefits you might be eligible for. You can write in Danish, English, or "
                "another language."
            ),
        }
    ]

# ---------------------------------------------------------------------------
# Hero banner
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="bh-hero">
        <h1>🇩🇰 Borger Hjælp</h1>
        <p>Describe your situation in your own words — I'll match you against Danish welfare schemes.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Render chat history
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    avatar = "🇩🇰" if msg["role"] == "assistant" else "🙋"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
user_input = st.chat_input("e.g. 'I'm 24, a full-time student in Aarhus, no income right now'")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🙋"):
        st.markdown(user_input)

    if not os.environ.get("GROQ_API_KEY"):
        with st.chat_message("assistant", avatar="🇩🇰"):
            warning = (
                "I need a GROQ_API_KEY to think — please add it to your `.env` file "
                "as `GROQ_API_KEY=your_key_here` and restart the app."
            )
            st.warning(warning)
            st.session_state.messages.append({"role": "assistant", "content": warning})
    else:
        with st.chat_message("assistant", avatar="🇩🇰"):
            with st.spinner("Reading your message..."):
                try:
                    st.session_state.profile = extract_profile(st.session_state.profile, user_input)
                except Exception as e:
                    st.error(f"Extraction error: {e}")
                    st.stop()

            with st.spinner("Checking eligibility against Danish welfare schemes..."):
                results = evaluate_all(st.session_state.profile, SCHEMES)

                lines = []
                for r in results:
                    status = "ELIGIBLE" if r.eligible else ("NEEDS_MORE_INFO" if r.missing_info else "NOT_ELIGIBLE")
                    lines.append(f"### {r.scheme.display_name} ({r.scheme.danish_name}) — {status}")
                    lines.append(f"Description: {r.scheme.description}")
                    for c in r.checks:
                        mark = "PASS" if c.passed else "FAIL"
                        lines.append(f"  - [{mark}] {c.rule_name}: {c.detail}")
                    if r.eligible:
                        lines.append(f"  Official URL: {r.scheme.official_url}")
                        lines.append(f"  Documents needed: {', '.join(r.scheme.documents_needed)}")
                    lines.append("")
                results_summary = "\n".join(lines)

            with st.spinner("Writing your personalized answer..."):
                try:
                    reply = explain_results(
                        results_summary,
                        conversation_language_hint=(
                            f"The user's most recent message (reply in THIS language, "
                            f"ignoring any Danish scheme/place names in it): {user_input}"
                        ),
                    )
                except Exception as e:
                    reply = (
                        "I matched your profile against the schemes but couldn't generate a "
                        f"nice explanation due to an error: {e}\n\nRaw results:\n\n{results_summary}"
                    )

            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})

            # -----------------------------------------------------------------
            # Colorful scheme-by-scheme status cards
            # -----------------------------------------------------------------
            with st.expander("🗂️ See status for every scheme (colored breakdown)", expanded=False):
                for r in results:
                    if r.eligible:
                        badge_class, badge_text = "badge-eligible", "ELIGIBLE"
                    elif r.missing_info:
                        badge_class, badge_text = "badge-needs-info", "NEEDS INFO"
                    else:
                        badge_class, badge_text = "badge-not-eligible", "NOT ELIGIBLE"

                    st.markdown(
                        f"""
                        <div class="scheme-card">
                            <b>{r.scheme.display_name}</b>
                            <span class="badge {badge_class}">{badge_text}</span>
                            <br><span style="color:#666;font-size:0.9rem;">{r.scheme.description}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            eligible_now = [r for r in results if r.eligible]
            if eligible_now:
                with st.expander("📋 Checklist for schemes you likely qualify for", expanded=True):
                    for r in eligible_now:
                        st.markdown(f"**{r.scheme.display_name}**")
                        st.markdown(f"- Apply at: {r.scheme.official_url}")
                        for doc in r.scheme.documents_needed:
                            st.checkbox(doc, key=f"{r.scheme.scheme_id}_{doc}")