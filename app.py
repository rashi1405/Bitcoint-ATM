import streamlit as st
import pandas as pd
import random

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(page_title="AI Lead Filtering & Qualification", layout="wide", page_icon="🤖")

# -----------------------------
# Header
# -----------------------------
st.markdown("""
<style>
    .metric-container {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 0 6px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Bitcoin ATM Lead Qualification POC")
st.markdown("### AI system for pre-filtering and qualifying potential ATM locations")

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.header("📂 Upload Lead Data")
uploaded_file = st.sidebar.file_uploader("Upload Leads Excel", type=["xlsx"])

# -----------------------------
# Configs
# -----------------------------
POP_THRESHOLD = 10000   # Minimum population
COMPETITOR_THRESHOLD = 2  # Max allowed ATMs nearby
DISALLOWED_STATES = ["New York"]

# -----------------------------
# Helper Functions
# -----------------------------
@st.cache_data
def get_competitor_count(zip_code):
    """Simulated competitor ATM count lookup."""
    return random.randint(0, 5)

def ai_call_simulation(lead):
    """Simulated AI call agent deciding if lead is 'interested'."""
    score = random.uniform(0, 1)
    return "Interested" if score > 0.4 else "Not Interested"

# -----------------------------
# Main Logic
# -----------------------------
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.markdown("### 📋 Uploaded Leads Preview")
    st.dataframe(df, use_container_width=True)

    # Validate columns
    required_cols = ["zip_code", "Blended Pop Estimate"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"❌ Missing required columns: {', '.join(missing)}")
        st.stop()

    # Add derived columns
    df["Population"] = df["Blended Pop Estimate"].fillna(0).astype(int)
    df["Competitors"] = df["zip_code"].apply(get_competitor_count)
    df["AI_Call_Status"] = df.apply(ai_call_simulation, axis=1)

    # Filtering
    df["RejectedReason"] = ""
    df["Qualified"] = True

    for i, row in df.iterrows():
        reasons = []
        if row["Population"] < POP_THRESHOLD:
            reasons.append("Low population")
        if row["Competitors"] > COMPETITOR_THRESHOLD:
            reasons.append("High market saturation")
        if row["AI_Call_Status"] != "Interested":
            reasons.append("Low interest")
        if "State" in df.columns and row["State"] in DISALLOWED_STATES:
            reasons.append("State not allowed")

        if reasons:
            df.at[i, "Qualified"] = False
            df.at[i, "RejectedReason"] = ", ".join(reasons)

    qualified = df[df["Qualified"] == True]
    rejected = df[df["Qualified"] == False]

    # -----------------------------
    # Results Tabs
    # -----------------------------
    st.markdown("---")
    st.subheader("📊 Lead Evaluation Results")

    tab1, tab2 = st.tabs(["✅ Qualified Leads", "❌ Rejected Leads"])

    with tab1:
        st.success(f"Qualified Leads: {len(qualified)}")
        st.dataframe(qualified, use_container_width=True)
        st.download_button(
            "📥 Download Qualified Leads",
            qualified.to_csv(index=False),
            "qualified_leads.csv",
            mime="text/csv"
        )

    with tab2:
        st.warning(f"Rejected Leads: {len(rejected)}")
        st.dataframe(rejected, use_container_width=True)
        st.download_button(
            "📥 Download Rejected Leads",
            rejected.to_csv(index=False),
            "rejected_leads.csv",
            mime="text/csv"
        )

    # -----------------------------
    # Summary Metrics
    # -----------------------------
    st.markdown("---")
    st.subheader("📈 Summary Insights")

    total = len(df)
    approved = len(qualified)
    rejection_rate = round((total - approved) / total * 100, 2)
    avg_population = int(df["Population"].mean())
    avg_competitors = round(df["Competitors"].mean(), 2)

    with st.container():
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Leads", total)
        col2.metric("Qualified Leads", approved)
        col3.metric("Rejection Rate", f"{rejection_rate}%")

        col1.metric("Avg Population (ZIP)", avg_population)
        col2.metric("Avg Competitors per ZIP", avg_competitors)
        col3.metric("Projected ROI Uplift", f"{round((approved/total)*100*2, 2)}%")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("⬆️ Please upload an Excel file to begin.")
