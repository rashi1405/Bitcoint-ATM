import streamlit as st
import pandas as pd
import folium
from geopy.geocoders import Nominatim
from streamlit.components.v1 import html

st.set_page_config(page_title="AI Lead Qualification POC", layout="wide")

st.title("🤖 Bitcoin ATM Lead Qualification POC")
st.markdown("### Automated filtering and qualification based on ZIP code metrics")

# -----------------------------
# Sidebar Input
# -----------------------------
st.sidebar.header("📂 Upload ZIP Code Data")
uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])

# -----------------------------
# Helper Functions
# -----------------------------
@st.cache_data
def get_location_coords(city, state):
    """Geocode ZIP region to coordinates for map visualization."""
    geolocator = Nominatim(user_agent="lead_locator")
    try:
        location = geolocator.geocode(f"{city}, {state}, USA", timeout=5)
        if location:
            return (location.latitude, location.longitude)
    except:
        return None
    return None

# -----------------------------
# Process Data
# -----------------------------
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.subheader("📋 Uploaded ZIP Code Data")
    st.dataframe(df)

    # Derived & Decision Columns
    df["Population"] = df["Blended Pop Estimate"]
    df["Competitors"] = df["total_kiosks"]
    df["AI_Call_Status"] = df["Location Analytics Flag"].apply(
        lambda x: "Interested" if str(x).lower() == "yes" else "Not Interested"
    )

    df["RejectedReason"] = ""
    df["Qualified"] = True

    # Qualification Logic
    for i, row in df.iterrows():
        reasons = []
        if row["Blended Pop Estimate"] < 10000:
            reasons.append("Below population threshold (<10,000)")
        if row["Pop Density"] < 400:
            reasons.append("Low population density (<400)")
        if row["total_kiosks"] > 2 or row["kiosks_installed"] > 2:
            reasons.append("High market saturation")
        if row["Removal Rate"] > 0.3:
            reasons.append("High removal rate")
        if row["AI_Call_Status"] != "Interested":
            reasons.append("Low interest (analytics flag)")

        if reasons:
            df.at[i, "Qualified"] = False
            df.at[i, "RejectedReason"] = ", ".join(reasons)

    # Split Qualified vs Rejected
    qualified = df[df["Qualified"] == True]
    rejected = df[df["Qualified"] == False]

    # Display Tables
    st.subheader("✅ Qualified ZIP Codes")
    st.dataframe(qualified[["zip_code", "City", "State", "Blended Pop Estimate", "Pop Density"]])

    st.subheader("❌ Rejected ZIP Codes")
    st.dataframe(rejected[["zip_code", "City", "State", "RejectedReason"]])

    # -----------------------------
    # Map Visualization
    # -----------------------------
    st.subheader("🗺️ ZIP Code Qualification Map")

    m = folium.Map(location=[37.0902, -95.7129], zoom_start=4)

    for _, row in qualified.iterrows():
        coords = get_location_coords(row["City"], row["State"])
        if coords:
            folium.Marker(
                location=coords,
                popup=f"{row['zip_code']} (Qualified)",
                icon=folium.Icon(color="green")
            ).add_to(m)

    for _, row in rejected.iterrows():
        coords = get_location_coords(row["City"], row["State"])
        if coords:
            folium.Marker(
                location=coords,
                popup=f"{row['zip_code']} ({row['RejectedReason']})",
                icon=folium.Icon(color="red")
            ).add_to(m)

    html(folium.Figure().add_child(m).render(), height=500)

    # -----------------------------
    # Summary Metrics
    # -----------------------------
    st.subheader("📊 Summary Insights")

    total = len(df)
    approved = len(qualified)
    rejection_rate = round((total - approved) / total * 100, 2)

    avg_population = int(df["Blended Pop Estimate"].mean())
    avg_density = int(df["Pop Density"].mean())

    col1, col2, col3 = st.columns(3)
    col1.metric("Total ZIPs", total)
    col2.metric("Qualified ZIPs", approved)
    col3.metric("Rejection Rate", f"{rejection_rate}%")

    col1.metric("Avg Population", avg_population)
    col2.metric("Avg Density", avg_density)
    col3.metric("Projected ROI Uplift", f"{round((approved/total)*100*2, 2)}%")

else:
    st.info("⬆️ Please upload an Excel with columns: `zip_code, City, State, Location Analytics Flag, Blended Pop Estimate, Pop Density, total_kiosks, kiosks_installed, Removal Rate`")
