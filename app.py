import streamlit as st
import pandas as pd
import requests
import time
from bs4 import BeautifulSoup
import re
from dotenv import load_dotenv
import os
load_dotenv()

# ----------------------------- 
# Page Config 
# ----------------------------- 
st.set_page_config(page_title="Bitcoin ATM Lead Qualification", layout="wide")
st.title("🤖 Bitcoin ATM Lead Qualification (Enhanced Version)")
st.markdown("### Upload ZIP codes and auto-filter based on population density")

# ----------------------------- 
# Sidebar Upload 
# ----------------------------- 
uploaded_file = st.sidebar.file_uploader("Upload Excel with ZIP Codes", type=["xlsx"])

# ----------------------------- 
# API Config & Thresholds
# ----------------------------- 
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
BLENDED_TRANSACTIONS_THRESHOLD = 10000
POP_DENSITY_THRESHOLD = 400

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
    """
    Fetches population for a given ZIP code from Census ACS API.
    Returns population count or 0 if error.
    """
    try:
        url = (
            "https://api.census.gov/data/2020/acs/acs5?"
            "get=B01003_001E,NAME"
            f"&for=zip%20code%20tabulation%20area:{zip_code}"
            f"&key={CENSUS_API_KEY}"
        )
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if len(data) > 1:
            population = int(data[1][0]) if data[1][0] else 0
            return population
        return 0
    except Exception as e:
        st.write(f"⚠️ Population fetch error for ZIP `{zip_code}`: {str(e)}")
        return 0

# ----------------------------- 
# Function to Fetch Area from Census GeoInfo API
# ----------------------------- 
def get_area(zip_code):
    """
    Fetches land area in square miles from Census GeoInfo API.
    Returns area in sq mi or 0 if error.
    """
    try:
        url = (
            "https://api.census.gov/data/2023/geoinfo?"
            "get=AREALAND_SQMI,AREALAND,INTPTLAT,INTPTLON,NAME"
            f"&for=zip%20code%20tabulation%20area:{zip_code}"
        )
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if len(data) > 1:
            area_sqmi = float(data[1][0]) if data[1][0] else 0
            return area_sqmi
        return 0
    except Exception as e:
        st.write(f"⚠️ Area fetch error for ZIP `{zip_code}`: {str(e)}")
        return 0

# ----------------------------- 
# Function to Fetch City and State from Zippopotam API
# ----------------------------- 
def get_city_state(zip_code):
    """
    Fetches city and state from Zippopotam API.
    Returns tuple (city, state, latitude, longitude) or ("Unknown", "Unknown", "Unknown", "Unknown") if error.
    """
    try:
        url = f"https://api.zippopotam.us/us/{zip_code}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "places" in data and len(data["places"]) > 0:
            city = data["places"][0].get("place name", "Unknown")
            state = data["places"][0].get("state abbreviation", "Unknown")
            latitude = data["places"][0].get("latitude", "Unknown")
            longitude = data["places"][0].get("longitude", "Unknown")
            return city, state, latitude, longitude
        return "Unknown", "Unknown", "Unknown", "Unknown" 
    except Exception as e:
        st.write(f"⚠️ City/State fetch error for ZIP `{zip_code}`: {str(e)}")
        return "Unknown", "Unknown", "Unknown", "Unknown"

# ----------------------------- 
# Function to Fetch All Data for a ZIP Code
# ----------------------------- 
def fetch_zip_data(zip_code):
    """
    Fetches population, area, city, and state for a ZIP code.
    Returns dictionary with all data.
    """
    population = get_population(zip_code)
    area = get_area(zip_code)
    city, state, latitude, longitude = get_city_state(zip_code)
    
    # Calculate population density
    pop_density = round(population / area, 2) if area > 0 else 0
    
    return {
        "Population": population,
        "Area_SqMi": area,
        "Pop_Density": pop_density,
        "City": city,
        "State": state,
        "Latitude": latitude,
        "Longitude": longitude
    }

# --------------------------------------------------
# NEW: Fetch Bitcoin ATMs/businesses for a location
# --------------------------------------------------
def get_bitcoin_locations(lat, lng, radius=1600):
    """
    Fetches Bitcoin-related businesses using Google Places API.
    Returns DataFrame with Bitcoin business information.
    """
    url = (
        f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        f"?location={lat},{lng}&radius={radius}&keyword=bitcoin&key={GOOGLE_API_KEY}"
    )
    
    results = []
    res = requests.get(url).json()
    
    for r in res.get("results", []):
        results.append({
            "place_id": r.get("place_id"),
            "name": r.get("name"),
            "address": r.get("vicinity"),
            "type": "bitcoin",
            "rating": r.get("rating", "N/A"),
        })
    
    return pd.DataFrame(results)

# --------------------------------------------------
# Fetch nearby POIs for categories
# --------------------------------------------------
def get_pois(lat, lng, radius=1600):
    """
    Fetches nearby points of interest using Google Places API.
    Returns DataFrame with business information.
    """
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
    """
    Fetches detailed information for a specific place.
    Returns dictionary with business details.
    """
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
    """
    Scrapes website for contact information and owner details.
    Returns dictionary with emails, phones, and owner information.
    """
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

# ----------------------------- 
# Main Logic 
# ----------------------------- 
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    
    st.markdown("### 📋 Uploaded ZIP Code Preview")
    st.dataframe(df, use_container_width=True)
    
    # Validate ZIP code column exists
    if "zip_code" not in df.columns:
        st.error("❌ Excel must contain a 'zip_code' column.")
        st.stop()
    
    # Keep only the zip_code column for processing
    df_processed = df[["zip_code"]].copy()
    
    # Ensure 5-digit zero-padded ZIP codes
    df_processed["zip_code"] = df_processed["zip_code"].astype(str).str.zfill(5)
    
    # Fetch data for each ZIP code
    st.info("📡 Fetching population, area, city, and state for each ZIP code...")
    
    progress_bar = st.progress(0)
    total_zips = len(df_processed)
    
    results = []
    for idx, zip_code in enumerate(df_processed["zip_code"]):
        zip_data = fetch_zip_data(zip_code)
        
        results.append(zip_data)
        
        # Update progress
        progress_bar.progress((idx + 1) / total_zips)
        
        # Add small delay to avoid rate limiting
        time.sleep(0.2)
    
    progress_bar.empty()
    
    # Add fetched data to dataframe
    results_df = pd.DataFrame(results)
    df_processed = pd.concat([df_processed, results_df], axis=1)
    
    # Qualification Rules: 
    # 1. Blended Transactions (Population from ACS) >= BLENDED_TRANSACTIONS_THRESHOLD
    # 2. Population Density >= POP_DENSITY_THRESHOLD
    
    df_processed["Qualified"] = (
        (df_processed["Population"] >= BLENDED_TRANSACTIONS_THRESHOLD) &
        (df_processed["Pop_Density"] >= POP_DENSITY_THRESHOLD)
    )
    
    # Detailed rejection reasons
    def get_rejection_reason(row):
        if row["Qualified"]:
            return ""
        reasons = []
        if row["Population"] < BLENDED_TRANSACTIONS_THRESHOLD:
            reasons.append(f"Low blended transactions/population ({row['Population']} < {BLENDED_TRANSACTIONS_THRESHOLD})")
        if row["Pop_Density"] < POP_DENSITY_THRESHOLD:
            reasons.append(f"Low density ({row['Pop_Density']} < {POP_DENSITY_THRESHOLD})")
        return " | ".join(reasons)
    
    df_processed["RejectedReason"] = df_processed.apply(get_rejection_reason, axis=1)
    
    qualified = df_processed[df_processed["Qualified"] == True]
    rejected = df_processed[df_processed["Qualified"] == False]
    
    # ----------------------------- 
    # Tabs for Results 
    # ----------------------------- 
    tab1, tab2 = st.tabs(["✅ Qualified Leads", "❌ Rejected Leads"])
    
    with tab1:
        st.success(f"Qualified Leads: {len(qualified)}")
        st.dataframe(qualified, use_container_width=True)
        
        # Download button
        csv = qualified.to_csv(index=False)
        st.download_button(
            label="📥 Download Qualified Leads",
            data=csv,
            file_name="qualified_leads.csv",
            mime="text/csv"
        )
    
    with tab2:
        st.warning(f"Rejected Leads: {len(rejected)}")
        st.dataframe(rejected, use_container_width=True)
        
        # Download button
        csv = rejected.to_csv(index=False)
        st.download_button(
            label="📥 Download Rejected Leads",
            data=csv,
            file_name="rejected_leads.csv",
            mime="text/csv"
        )
    
    # ----------------------------- 
    # Summary Metrics 
    # ----------------------------- 
    st.markdown("---")
    st.subheader("📊 Summary Metrics")
    
    total = len(df_processed)
    approved = len(qualified)
    rejection_rate = round((total - approved) / total * 100, 2) if total > 0 else 0
    avg_population = int(df_processed["Population"].mean()) if total > 0 else 0
    avg_density = round(df_processed["Pop_Density"].mean(), 2) if total > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total ZIP Codes", total)
    col2.metric("Qualified", approved)
    col3.metric("Rejection Rate", f"{rejection_rate}%")
    col4.metric("Avg Blended Trans (Pop)", avg_population)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Avg Pop Density", f"{avg_density} /sq mi")
    col2.metric("Total States", df_processed["State"].nunique())
    col3.metric("Total Cities", df_processed["City"].nunique())
    
    # --------------------------------------------------
    # ORIGINAL FEATURE: PROCESS QUALIFIED ZIP CODES FOR BUSINESSES (INCLUDING BITCOIN ATMs)
    # --------------------------------------------------
    if len(qualified) > 0 and GOOGLE_API_KEY and GOOGLE_API_KEY != "":
        st.markdown("---")
        st.subheader("📍 Fetch Businesses + Bitcoin ATMs + Owner Details for Qualified ZIPs")
        
        if st.button("🚀 Start Business Search (Includes Bitcoin ATMs)", type="primary"):
            all_results = []
            
            business_progress = st.progress(0)
            total_qualified = len(qualified)
            
            for idx, (_, row) in enumerate(qualified.iterrows()):
                zip_code = row["zip_code"]
                lat = row["Latitude"]
                lng = row["Longitude"]
                
                st.write(f"### Processing ZIP: `{zip_code}` ({idx+1}/{total_qualified})")
                
                # Check if we have valid coordinates
                if lat == "Unknown" or lng == "Unknown":
                    st.warning(f"⚠️ Skipping {zip_code} - No valid coordinates")
                    business_progress.progress((idx + 1) / total_qualified)
                    continue
                
                try:
                    lat = float(lat)
                    lng = float(lng)
                except:
                    st.warning(f"⚠️ Skipping {zip_code} - Invalid coordinates")
                    business_progress.progress((idx + 1) / total_qualified)
                    continue
                
                # Fetch nearby businesses (regular categories)
                poi_df = get_pois(lat, lng)
                
                # Fetch Bitcoin ATMs/locations
                bitcoin_df = get_bitcoin_locations(lat, lng)
                
                st.write(f"Found {len(poi_df)} regular businesses + {len(bitcoin_df)} Bitcoin locations")
                
                # Process regular businesses
                if len(poi_df) > 0:
                    st.dataframe(poi_df, use_container_width=True)
                    
                    # Fetch details for each business
                    for _, poi in poi_df.iterrows():
                        try:
                            details = get_place_details(poi["place_id"])
                            website = details.get("website")
                            
                            # Scrape owner info if website exists
                            owner_data = scrape_owner_info(website) if website else {"emails": [], "phones": [], "owner_lines": []}
                            
                            all_results.append({
                                "ZIP": zip_code,
                                "City": row["City"],
                                "State": row["State"],
                                "Business Name": poi["name"],
                                "Address": poi["address"],
                                "Category": poi["type"],
                                "Phone": details.get("formatted_phone_number"),
                                "Website": website,
                                "Owner Emails": ", ".join(owner_data["emails"]) if owner_data["emails"] else "",
                                "Owner Phones (Scraped)": ", ".join(owner_data["phones"]) if owner_data["phones"] else "",
                                "Owner Info Lines": " | ".join(owner_data["owner_lines"]) if owner_data["owner_lines"] else ""
                            })
                            
                            # Small delay to avoid rate limiting
                            time.sleep(0.3)
                        except Exception as e:
                            st.write(f"⚠️ Error fetching details for {poi['name']}: {str(e)}")
                
                # Process Bitcoin ATM locations
                if len(bitcoin_df) > 0:
                    st.write(f"**Bitcoin Locations Found:**")
                    st.dataframe(bitcoin_df, use_container_width=True)
                    
                    # Fetch details for each Bitcoin location
                    for _, btc in bitcoin_df.iterrows():
                        try:
                            details = get_place_details(btc["place_id"])
                            website = details.get("website")
                            
                            # Scrape owner info if website exists
                            owner_data = scrape_owner_info(website) if website else {"emails": [], "phones": [], "owner_lines": []}
                            
                            all_results.append({
                                "ZIP": zip_code,
                                "City": row["City"],
                                "State": row["State"],
                                "Business Name": btc["name"],
                                "Address": btc["address"],
                                "Category": "bitcoin_atm",
                                "Phone": details.get("formatted_phone_number"),
                                "Website": website,
                                "Owner Emails": ", ".join(owner_data["emails"]) if owner_data["emails"] else "",
                                "Owner Phones (Scraped)": ", ".join(owner_data["phones"]) if owner_data["phones"] else "",
                                "Owner Info Lines": " | ".join(owner_data["owner_lines"]) if owner_data["owner_lines"] else ""
                            })
                            
                            # Small delay to avoid rate limiting
                            time.sleep(0.3)
                        except Exception as e:
                            st.write(f"⚠️ Error fetching details for {btc['name']}: {str(e)}")
                
                business_progress.progress((idx + 1) / total_qualified)
                time.sleep(0.5)  # Delay between ZIPs
            
            business_progress.empty()
            
            # Display final results
            if len(all_results) > 0:
                final_df = pd.DataFrame(all_results)
                
                st.markdown("## 🏁 Final Results (All Businesses + Bitcoin ATMs + Owner Info)")
                st.success(f"Found {len(final_df)} total businesses (including Bitcoin ATMs) across {len(qualified)} qualified ZIP codes")
                
                # Show breakdown by category
                st.write("**Breakdown by Category:**")
                category_counts = final_df["Category"].value_counts()
                st.dataframe(category_counts, use_container_width=True)
                
                # Split results based on contact availability
                # Has contact if either Phone or Owner Phones (Scraped) is not empty
                has_contact = final_df[
                    (final_df["Phone"].notna() & (final_df["Phone"] != "")) | 
                    (final_df["Owner Phones (Scraped)"].notna() & (final_df["Owner Phones (Scraped)"] != ""))
                ]
                
                no_contact = final_df[
                    (final_df["Phone"].isna() | (final_df["Phone"] == "")) & 
                    (final_df["Owner Phones (Scraped)"].isna() | (final_df["Owner Phones (Scraped)"] == ""))
                ]
                
                # Create tabs for contact/no-contact results
                contact_tab1, contact_tab2 = st.tabs([
                    f"📞 With Contact Info ({len(has_contact)})", 
                    f"❌ Without Contact Info ({len(no_contact)})"
                ])
                
                with contact_tab1:
                    st.success(f"Businesses with contact information: {len(has_contact)}")
                    st.dataframe(has_contact, use_container_width=True)
                    
                    if len(has_contact) > 0:
                        st.download_button(
                            label="📥 Download Businesses WITH Contact Info",
                            data=has_contact.to_csv(index=False),
                            file_name="businesses_with_contact.csv",
                            mime="text/csv",
                        )
                
                with contact_tab2:
                    st.warning(f"Businesses without contact information: {len(no_contact)}")
                    st.dataframe(no_contact, use_container_width=True)
                    
                    if len(no_contact) > 0:
                        st.download_button(
                            label="📥 Download Businesses WITHOUT Contact Info",
                            data=no_contact.to_csv(index=False),
                            file_name="businesses_without_contact.csv",
                            mime="text/csv",
                        )
            else:
                st.warning("No businesses found in qualified ZIP codes")

else:
    st.info("⬆️ Please upload an Excel file with a 'zip_code' column to continue.")
    st.markdown("""
    ### 📝 Instructions:
    1. Upload an Excel file (.xlsx) with a column named **`zip_code`**
    2. The system will fetch:
       - **Population** (Census ACS API) - Used as Blended Transactions
       - **Land Area** in sq mi (Census GeoInfo API)
       - **Population Density** (calculated as Population / Area)
       - **City and State** (Zippopotam API)
    3. **Qualification Criteria:**
       - Blended Transactions (Population) ≥ 10,000
       - Population Density ≥ 400 people/sq mi
    4. Download qualified, rejected, or all data as CSV
    5. **New Feature:** Search for Bitcoin ATMs and related businesses in qualified ZIPs
    6. **Optional:** Add Google Maps API Key to search for other businesses in qualified ZIPs
    """)