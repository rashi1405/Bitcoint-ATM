# 🤖 Bitcoin ATM Lead Qualification POC

An **AI-powered Streamlit web app** that automatically filters and qualifies potential Bitcoin ATM locations using population data, competition levels, and simulated AI calling results.
This helps identify the most promising ZIP codes before passing leads to sales teams.

---

## 🚀 Features

✅ **Excel Upload (ZIP-based)**
Upload an `.xlsx` file containing ZIP code data (and optional city, state, population metrics, etc.)

✅ **Automated Filtering**
Each ZIP is scored and filtered based on:

* Population threshold
* Competitor ATM density
* Simulated AI call results (lead interest)

✅ **AI Call Simulation**
A mock agent determines if the lead shows "Interest" based on probabilistic scoring.

✅ **Dynamic DataFrame Views**
See both:

* **Qualified Leads** — likely high-performing areas
* **Rejected Leads** — filtered with reasons for disqualification

✅ **Summary Dashboard**
Quick KPIs like:

* Total Leads
* Qualified Count
* Rejection Rate
* Avg. ZIP Population
* Avg. Competitor Count
* Projected ROI Uplift

✅ **Interactive Display**
All tables are scrollable and can be filtered directly in Streamlit.

---

## 🧩 Tech Stack

| Component             | Description                                    |
| --------------------- | ---------------------------------------------- |
| **Python 3.10+**      | Core programming language                      |
| **Streamlit**         | Interactive web app framework                  |
| **Pandas**            | Data manipulation and Excel parsing            |
| **Folium** (optional) | Map visualization for qualified/rejected leads |
| **Geopy** (optional)  | Geocoding support (currently commented out)    |

---

## 📂 File Upload Format

Your Excel file should contain at least this column:

* `zip_code`

Optionally, it can also include:

* `City`
* `State`
* `Blended Pop Estimate`
* `Pop Density`
* `total_kiosks`
* `Margin`
* `Location Analytics Flag`

🧾 Example (Excel):

| zip_code | City        | State | Blended Pop Estimate | Pop Density | total_kiosks |
| -------- | ----------- | ----- | -------------------- | ----------- | ------------ |
| 90001    | Los Angeles | CA    | 22500                | 1200        | 5            |
| 73301    | Austin      | TX    | 38000                | 1800        | 1            |

---

## ⚙️ Configuration Parameters

You can tweak these in the code to change filtering rules:

```python
POP_THRESHOLD = 10000         # Minimum population for qualification
COMPETITOR_THRESHOLD = 2      # Max allowed nearby ATMs
DISALLOWED_STATES = ["New York"]
```

---

## 💡 How It Works

1. Upload an Excel file with ZIP code data.
2. The app enriches each row with simulated:

   * Population
   * Competitor count
   * AI call outcome
3. Filtering logic classifies each lead as **Qualified** or **Rejected**.
4. A detailed dashboard summarizes the results.

---

## 📊 Output Sections

* **Uploaded Leads** — Displays all uploaded data
* **✅ Qualified Leads** — Leads that meet all thresholds
* **❌ Rejected Leads** — Leads filtered out with detailed reasons
* **📈 Summary Insights** — Metrics and calculated averages

---

## 🧠 Future Enhancements

* Integrate **real Census API** for accurate population data
* Use **Google Places API** or **Yelp API** for competitor lookups
* Replace simulated AI call logic with an **LLM-based interest classifier**
* Enable **map visualization** with `folium` markers for approved/rejected ZIPs

---

## 🧪 Run Locally

### 1️⃣ Install Dependencies

```bash
pip install streamlit pandas openpyxl geopy folium
```

### 2️⃣ Run the App

```bash
streamlit run app.py
```

### 3️⃣ Open in Browser

Navigate to:

```
http://localhost:8501
```

---
