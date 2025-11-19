import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(page_title="Bitcoin ATM Lead Qualification", layout="wide")
st.title("🤖 Bitcoin ATM Lead Qualification (Full Version)")
st.markdown("### Upload ZIP codes → Check population → Fetch nearby businesses → Scrape owner info")

# --------------------------------------------------
# API KEYS
# --------------------------------------------------
CENSUS_API_KEY = "709969d12c0868636e5253e3646270cc9f4de135"
GOOGLE_API_KEY = "YOUR_GOOGLE_MAPS_API_KEY_HERE"

POP_THRESHOLD = 10000   # Minimum population to qualify


# --------------------------------------------------
# GOOGLE PLACE TYPES TO SEARCH
# --------------------------------------------------
PLACE_TYPES = [
    "gas_station",
    "convenience_store",
    "supermarket",
    "liquor_store",
    "pharmacy",
    "jewelry_store",
    "laundry",
    "shopping_mall",
    "restaurant",
]


# --------------------------------------------------
# Fetch population for a ZIP from Census
# --------------------------------------------------
def get_population(zip_code):
    try:
        url = (
            f"https://api.census.gov/data/2023/acs/acs5?"
            f"get=B01003_001E&for=zip%20code%20tabulation%20area:{zip_code}"
            f"&key={CENSUS_API_KEY}"
        )

        response = requests.get(url)
        data = response.json()

        population = int(data[1][0])
        return population

    except Exception:
        return 0


# --------------------------------------------------
# Geocode ZIP → lat/lng using Google Maps
# --------------------------------------------------
def geocode_zip(zip_code):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={zip_code}&key={GOOGLE_API_KEY}"
    res = requests.get(url).json()

    if res.get("status") != "OK":
        return None, None

    location = res["results"][0]["geometry"]["location"]
    return location["lat"], location["lng"]


# --------------------------------------------------
# Fetch nearby POIs for categories
# --------------------------------------------------
def get_pois(lat, lng, radius=1600):
    results = []

    for place_type in PLACE_TYPES:
        url = (
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            f"?location={lat},{lng}&radius={radius}&type={place_type}&key={GOOGLE_API_KEY}"
        )

        res = requests.get(url).json()

        for r in res.get("results", []):
            results.append({
                "place_id": r.get("place_id"),
                "name": r.get("name"),
                "address": r.get("vicinity"),
                "type": place_type,
            })

    return pd.DataFrame(results)


# --------------------------------------------------
# Fetch business details (phone, website, hours)
# --------------------------------------------------
def get_place_details(place_id):
    url = (
        f"https://maps.googleapis.com/maps/api/place/details/json"
        f"?place_id={place_id}&fields=name,formatted_phone_number,website,opening_hours"
        f"&key={GOOGLE_API_KEY}"
    )

    res = requests.get(url).json()
    return res.get("result", {})


# --------------------------------------------------
# Scrape website for owner emails / phones
# --------------------------------------------------
def scrape_owner_info(website):
    try:
        html = requests.get(website, timeout=5).text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)

        emails = list(set(re.findall(r'\S+@\S+\.\S+', text)))
        phones = list(set(re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)))

        owner_kw = ["owner", "manager", "founder", "ceo"]
        owner_lines = [line for line in text.split(".") if any(k in line.lower() for k in owner_kw)]

        return {
            "emails": emails,
            "phones": phones,
            "owner_lines": owner_lines[:5]
        }

    except Exception:
        return {"emails": [], "phones": [], "owner_lines": []}


# --------------------------------------------------
# FILE UPLOAD
# --------------------------------------------------
uploaded_file = st.sidebar.file_uploader("Upload Excel with ZIP Codes", type=["xlsx"])


# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------
if uploaded_file:
    df = pd.read_excel(uploaded_file)

    st.markdown("### 📋 Uploaded ZIP Code Preview")
    st.dataframe(df)

    if "zip_code" not in df.columns:
        st.error("Excel must contain a 'zip_code' column.")
        st.stop()

    df["zip_code"] = df["zip_code"].astype(str).str.zfill(5)

    st.info("📡 Fetching population for each ZIP...")
    df["Population"] = df["zip_code"].apply(get_population)

    df["Qualified"] = df["Population"] >= POP_THRESHOLD
    df["RejectedReason"] = df.apply(
        lambda row: "Low population" if not row["Qualified"] else "",
        axis=1
    )

    qualified = df[df["Qualified"]]
    rejected = df[~df["Qualified"]]

    tab1, tab2 = st.tabs(["Qualified ZIPs", "Rejected ZIPs"])

    with tab1:
        st.success(f"Qualified ZIP Codes: {len(qualified)}")
        st.dataframe(qualified)

    with tab2:
        st.warning(f"Rejected ZIPs: {len(rejected)}")
        st.dataframe(rejected)

    # --------------------------------------------------
    # PROCESS QUALIFIED ZIP CODES
    # --------------------------------------------------
    st.markdown("---")
    st.subheader("📍 Fetching Businesses + Owner Details")

    all_results = []

    for _, row in qualified.iterrows():
        zip_code = row["zip_code"]
        st.write(f"### Processing ZIP: `{zip_code}`")

        lat, lng = geocode_zip(zip_code)
        if not lat:
            st.error(f"Failed to geocode {zip_code}")
            continue

        poi_df = get_pois(lat, lng)

        st.write("Found Businesses:", len(poi_df))
        st.dataframe(poi_df)

        for _, poi in poi_df.iterrows():
            details = get_place_details(poi["place_id"])
            website = details.get("website")

            owner_data = scrape_owner_info(website) if website else {"emails": [], "phones": [], "owner_lines": []}

            all_results.append({
                "ZIP": zip_code,
                "Business Name": poi["name"],
                "Address": poi["address"],
                "Category": poi["type"],
                "Phone": details.get("formatted_phone_number"),
                "Website": website,
                "Owner Emails": owner_data["emails"],
                "Owner Phones (Scraped)": owner_data["phones"],
                "Owner Info Lines": owner_data["owner_lines"]
            })

    final_df = pd.DataFrame(all_results)

    st.markdown("## 🏁 Final Results (Businesses + Owner Info)")
    st.dataframe(final_df, use_container_width=True)

    # Download button
    st.download_button(
        label="📥 Download Full Results as CSV",
        data=final_df.to_csv(index=False),
        file_name="lead_results.csv",
        mime="text/csv",
    )

else:
    st.info("⬆️ Upload a ZIP code Excel file to continue.")
