import streamlit as st
import pandas as pd
import requests

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(page_title="Bitcoin ATM Lead Qualification", layout="wide")

st.title("🤖 Bitcoin ATM Lead Qualification (Simplified Version)")
st.markdown("### Upload ZIP codes and auto-filter based on population")

# -----------------------------
# Sidebar Upload
# -----------------------------
uploaded_file = st.sidebar.file_uploader("Upload Excel with ZIP Codes", type=["xlsx"])

# -----------------------------
# Census API Config
# -----------------------------
CENSUS_API_KEY = "709969d12c0868636e5253e3646270cc9f4de135"
POP_THRESHOLD = 10000

# -----------------------------
# Function to Fetch Population for Single ZIP Code
# -----------------------------
def get_population(zip_code):
    """
    Calls Census API for a single ZIP code and returns population.
    """
    try:
        # url = (
        #     f"https://api.census.gov/data/2020/acs/acs5?"
        #     f"get=B01003_001E&for=zip%20code%20tabulation%20area:{zip_code}"
        #     f"&key={CENSUS_API_KEY}"
        # ) 
        url = (
            "https://api.census.gov/data/2020/acs/acs5?"
            "get=NAME,B01003_001E"
            f"&for=zip%20code%20tabulation%20area:{zip_code}"
            f"&key={CENSUS_API_KEY}"
        )
        
        response = requests.get(url)
        data = response.json()
          
        # Print entire response for debugging
        st.write(f"### Raw Census Response for ZIP `{zip_code}`")
        st.json(data)

        population = int(data[1][0])  # Extract population field
        return population

    except Exception:
        st.write(f"No data for ZIP `{zip_code}`")
       
        return 0  # if any error, treat as 0 population


# -----------------------------
# Main Logic
# -----------------------------
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.markdown("### 📋 Uploaded ZIP Code Preview")
    st.dataframe(df, use_container_width=True)

    if "zip_code" not in df.columns:
        st.error("❌ Excel must contain a 'zip_code' column.")
        st.stop()

    # Ensure 5-digit zero-padded ZIP codes
    df["zip_code"] = df["zip_code"].astype(str).str.zfill(5)

    # Fetch Census population for each ZIP
    st.info("📡 Fetching population for each ZIP code...")
    df["Population"] = df["zip_code"].apply(get_population)

    # Qualification Rule
    df["Qualified"] = df["Population"] >= POP_THRESHOLD
    df["RejectedReason"] = df.apply(
        lambda row: "Low population" if not row["Qualified"] else "",
        axis=1
    )

    qualified = df[df["Qualified"] == True]
    rejected = df[df["Qualified"] == False]

    # -----------------------------
    # Tabs for Results
    # -----------------------------
    tab1, tab2 = st.tabs(["✅ Qualified Leads", "❌ Rejected Leads"])

    with tab1:
        st.success(f"Qualified Leads: {len(qualified)}")
        st.dataframe(qualified, use_container_width=True)

    with tab2:
        st.warning(f"Rejected Leads: {len(rejected)}")
        st.dataframe(rejected, use_container_width=True)

    # -----------------------------
    # Summary Metrics
    # -----------------------------
    st.markdown("---")
    st.subheader("📊 Summary Metrics")

    total = len(df)
    approved = len(qualified)
    rejection_rate = round((total - approved) / total * 100, 2)
    avg_population = int(df["Population"].mean())

    col1, col2, col3 = st.columns(3)
    col1.metric("Total ZIP Codes", total)
    col2.metric("Qualified", approved)
    col3.metric("Rejection Rate", f"{rejection_rate}%")

    col1.metric("Avg Population", avg_population)
else:
    st.info("⬆️ Please upload an Excel file to continue.")
