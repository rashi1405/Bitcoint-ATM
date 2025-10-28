import streamlit as st
import pandas as pd
import requests
from geopy.geocoders import Nominatim
import folium
from streamlit.components.v1 import html
import random

st.set_page_config(page_title="AI Lead Filtering & Qualification", layout="wide")

st.title("🤖 Bitcoin ATM Lead Qualification POC")
st.markdown("### AI system for pre-filtering and qualifying potential ATM locations")

# -----------------------------
# Sidebar Input
# -----------------------------
st.sidebar.header("📂 Upload Lead Data")
uploaded_file = st.sidebar.file_uploader("Upload Leads Excel (zip_code)", type=["xlsx"])

# Dummy Configs
POP_THRESHOLD = 10000  # Minimum population
COMPETITOR_THRESHOLD = 2  # Max allowed ATMs nearby
DISALLOWED_STATES = ["New York"]

# -----------------------------
# Helper Functions
# -----------------------------

@st.cache_data
def get_population(zip_code):
    """Simulated population lookup."""
    # For real: use Census API
    return random.randint(5000, 50000)

@st.cache_data
def get_competitor_count(zip_code):
    """Simulated competitor ATM count lookup."""
    return random.randint(0, 5)

# @st.cache_data
# def validate_phone(phone):
#     """Simple phone number validation."""
#     digits = ''.join(filter(str.isdigit, phone))
#     return len(digits) >= 10

def ai_call_simulation(lead):
    """Simulated AI call agent deciding if lead is 'interested'."""
    # Randomized, but influenced by name or zip
    score = random.uniform(0, 1)
    return "Interested" if score > 0.4 else "Not Interested"

# def get_location_coords(address):
#     """Geocode address."""
#     geolocator = Nominatim(user_agent="lead_locator")
#     try:
#         location = geolocator.geocode(address, timeout=5)
#         if location:
#             return (location.latitude, location.longitude)
#     except:
#         return None
#     return None

# -----------------------------
# Process Leads
# -----------------------------
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.subheader("📋 Uploaded Leads")
    st.dataframe(df)

    # Add derived columns
    df["Population"] = df["zip_code"].apply(get_population)
    df["Competitors"] = df["zip_code"].apply(get_competitor_count)
    # df["PhoneValid"] = df["phone"].apply(validate_phone)
    df["AI_Call_Status"] = df.apply(ai_call_simulation, axis=1)

    # Filter Logic
    df["RejectedReason"] = ""
    df["Qualified"] = True

    for i, row in df.iterrows():
        reasons = []
        if row["Population"] < POP_THRESHOLD:
            reasons.append("Low population")
        if row["Competitors"] > COMPETITOR_THRESHOLD:
            reasons.append("High market saturation")
        # if not row["PhoneValid"]:
        #     reasons.append("Invalid phone")
        if row["AI_Call_Status"] != "Interested":
            reasons.append("Low interest")

        if reasons:
            df.at[i, "Qualified"] = False
            df.at[i, "RejectedReason"] = ", ".join(reasons)

    qualified = df[df["Qualified"] == True]
    rejected = df[df["Qualified"] == False]

    st.subheader("✅ Qualified Leads")
    st.dataframe(qualified)

    st.subheader("❌ Rejected Leads")
    st.dataframe(rejected)


    # -----------------------------
    # Map Visualization
    # -----------------------------
    # st.subheader("🗺️ Qualified Lead Locations Map")

    # m = folium.Map(location=[37.0902, -95.7129], zoom_start=4)

    # for _, row in qualified.iterrows():
    #     coords = get_location_coords(row["address"])
    # if coords:
    #     folium.Marker(
    #         location=coords,
    #         popup=f"({row['zip_code']})",
    #         icon=folium.Icon(color="green")
    #     ).add_to(m)

    # for _, row in rejected.iterrows():
    #     coords = get_location_coords(row["address"])
    #     if coords:
    #         folium.Marker(
    #             location=coords,
    #             popup=f"({row['RejectedReason']})",
    #             icon=folium.Icon(color="red")
    #         ).add_to(m)

    # html(folium.Figure().add_child(m).render(), height=500)


    # -----------------------------
    # Summary Metrics
    # -----------------------------
    st.subheader("📊 Summary Insights")

    total = len(df)
    approved = len(qualified)
    rejection_rate = round((total - approved) / total * 100, 2)

    avg_population = int(df["Population"].mean())
    avg_competitors = round(df["Competitors"].mean(), 2)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Leads", total)
    col2.metric("Qualified Leads", approved)
    col3.metric("Rejection Rate", f"{rejection_rate}%")

    col1.metric("Avg Population (ZIP)", avg_population)
    col2.metric("Avg Competitors per ZIP", avg_competitors)
    col3.metric("Projected ROI Uplift", f"{round((approved/total)*100*2, 2)}%")

else:
    st.info("⬆️ Please upload a Excel with columns: `zip_code` to begin.")

# zip_code	City	State	Location Analytics Flag	Blended Pop Estimate	Pop Density	Square Miles	total_kiosks	bcd_kiosks	Margin	kiosks_installed	kiosks_pending_removal	kiosks_removed	Removal Rate
