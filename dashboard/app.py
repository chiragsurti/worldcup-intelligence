"""World Cup Intelligence Platform — Streamlit Dashboard."""

import json
import os
import sys
from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/worldcup.db")


@st.cache_resource
def get_db_engine():
    return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def load_table(table_name: str, where_clause: str = "") -> pd.DataFrame:
    """Load a table into a DataFrame."""
    engine = get_db_engine()
    query = f"SELECT * FROM {table_name}"
    if where_clause:
        query += f" WHERE {where_clause}"
    query += " ORDER BY created_at DESC"
    try:
        return pd.read_sql(query, engine)
    except Exception:
        return pd.DataFrame()


# --- Page config ---
st.set_page_config(
    page_title="World Cup 2026 Intelligence",
    page_icon="⚽",
    layout="wide",
)

st.title("⚽ World Cup 2026 Intelligence Platform")
st.caption("AI-powered pre-match briefings, predictions, and media packs")

# --- Sidebar ---
today = date.today().isoformat()
selected_date = st.sidebar.date_input("Match Date", value=date.today())
date_str = selected_date.isoformat()

# --- Navigation ---
page = st.sidebar.radio("Navigate", ["📋 Schedule", "🃏 Predictions", "🔍 Audit Trail", "📦 Media Pack"])

# --- Schedule Page ---
if page == "📋 Schedule":
    st.header(f"📋 Match Schedule — {date_str}")

    df = load_table("fixtures", f"match_date = '{date_str}'")
    if df.empty:
        st.info("No fixtures found for this date. Run the agent to fetch schedule data.")
    else:
        for _, row in df.iterrows():
            col1, col2, col3 = st.columns([3, 1, 3])
            with col1:
                st.markdown(f"### 🏠 {row['home_team']}")
            with col2:
                st.markdown("### vs")
            with col3:
                st.markdown(f"### ✈️ {row['away_team']}")
            st.caption(f"📍 {row.get('venue', 'TBD')} | Status: {row.get('status', 'scheduled')}")
            st.divider()

# --- Predictions Page ---
elif page == "🃏 Predictions":
    st.header(f"🃏 Prediction Cards — {date_str}")

    df = load_table("prediction_cards")
    if df.empty:
        st.info("No predictions generated yet. Run the agent pipeline to generate prediction cards.")
    else:
        # Join with fixtures for team names
        fixtures_df = load_table("fixtures")

        for _, row in df.iterrows():
            match_id = row["match_id"]
            fixture = fixtures_df[fixtures_df["match_id"] == match_id]

            if not fixture.empty:
                home = fixture.iloc[0]["home_team"]
                away = fixture.iloc[0]["away_team"]
                title = f"{home} vs {away}"
            else:
                title = f"Match {match_id}"

            with st.expander(f"🃏 {title}", expanded=True):
                # Probability bars
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Home Win", f"{row['prob_home']*100:.0f}%")
                    st.progress(float(row["prob_home"]))
                with col2:
                    st.metric("Draw", f"{row['prob_draw']*100:.0f}%")
                    st.progress(float(row["prob_draw"]))
                with col3:
                    st.metric("Away Win", f"{row['prob_away']*100:.0f}%")
                    st.progress(float(row["prob_away"]))

                st.markdown("**Analysis:**")
                st.write(row.get("analysis", ""))
                st.markdown("**Reasoning:**")
                st.write(row.get("reasoning", ""))

# --- Audit Trail Page ---
elif page == "🔍 Audit Trail":
    st.header("🔍 Audit Trail — Grounded Claims")

    df = load_table("audit_claims")
    if df.empty:
        st.info("No audit claims recorded yet. Run the agent pipeline to ground facts.")
    else:
        # Status filter
        status_filter = st.multiselect(
            "Filter by status",
            options=["Confirmed", "Reported", "Unverified"],
            default=["Confirmed", "Reported", "Unverified"],
        )
        filtered = df[df["status_label"].isin(status_filter)]

        for _, row in filtered.iterrows():
            status = row["status_label"]
            badge_color = {"Confirmed": "🟢", "Reported": "🟡", "Unverified": "🔴"}.get(status, "⚪")

            with st.expander(f"{badge_color} [{status}] {row['claim_text'][:80]}..."):
                st.markdown(f"**Match ID:** {row['match_id']}")
                st.markdown(f"**Confidence:** {row['confidence_score']:.0%}")
                st.markdown(f"**Status:** {badge_color} {status}")

                # Citations
                try:
                    citations = json.loads(row["citations"]) if row["citations"] else []
                except (json.JSONDecodeError, TypeError):
                    citations = []

                if citations:
                    st.markdown("**Citations:**")
                    for cite in citations:
                        st.markdown(
                            f"- [{cite.get('title', 'Untitled')}]({cite.get('url', '#')}) "
                            f"— *{cite.get('publisher', 'Unknown')}* ({cite.get('publish_time', 'N/A')})"
                        )
                        if cite.get("quote_snippet"):
                            st.caption(f'> "{cite["quote_snippet"]}"')

# --- Media Pack Page ---
elif page == "📦 Media Pack":
    st.header("📦 Media Packs")

    df = load_table("media_packs")
    if df.empty:
        st.info("No media packs generated yet. Run the agent pipeline to create content.")
    else:
        fixtures_df = load_table("fixtures")

        for _, row in df.iterrows():
            match_id = row["match_id"]
            fixture = fixtures_df[fixtures_df["match_id"] == match_id]

            if not fixture.empty:
                title = f"{fixture.iloc[0]['home_team']} vs {fixture.iloc[0]['away_team']}"
            else:
                title = f"Match {match_id}"

            with st.expander(f"📦 {title}"):
                tab1, tab2 = st.tabs(["📧 Email Preview", "🐦 Social Thread"])

                with tab1:
                    if row.get("email_html"):
                        st.components.v1.html(row["email_html"], height=400, scrolling=True)
                    else:
                        st.info("No email content generated.")

                with tab2:
                    try:
                        threads = json.loads(row["social_threads"]) if row["social_threads"] else []
                    except (json.JSONDecodeError, TypeError):
                        threads = []

                    if threads:
                        for i, tweet in enumerate(threads, 1):
                            st.markdown(f"**{i}/{len(threads)}** — {tweet}")
                            st.caption(f"{len(tweet)} chars")
                        # Copy button
                        full_thread = "\n\n".join(f"{i}/{len(threads)} {t}" for i, t in enumerate(threads, 1))
                        st.code(full_thread, language=None)
                    else:
                        st.info("No social thread generated.")
