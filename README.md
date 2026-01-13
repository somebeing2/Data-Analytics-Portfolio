# Data-Analytics-Portfolio
# DiviTrack: Intelligent Dividend & Tax Auditor

**DiviTrack** is a specialized analytics dashboard built for Indian investors to track dividend income and automate tax liability estimations.

Unlike standard portfolio trackers, it features a **Compliance Engine** that automatically applies Indian Tax Deducted at Source (TDS) logic (Section 194) and allows investors to toggle between **Calendar Year** (performance view) and **Financial Year** (tax filing view).

🔗 **Live Demo:** [https://data-analytics-portfolio-dejuau9q8zexweqq39pxe2.streamlit.app/]

---

###  Key Features

* ** Auto-TDS Compliance Engine:**
    * Automatically detects if aggregate dividends from a single company exceed **₹5,000** in a Financial Year.
    * Applies **10% TDS** only to eligible transactions, removing manual guesswork.
* ** "Time Machine" Architecture:**
    * **Dual-Timeline Support:** Instantly switch between **Calendar Year** (Jan-Dec) and **Financial Year** (Apr-Mar) without reloading data.
    * **Quarterly Drill-Down:** Filter by specific quarters (e.g., *Q3 FY24-25*) to audit granular earnings.
* ** Asset Support:**
    * Supports **Stocks**, **REITs**, and **InvITs** (e.g., Embassy, PowerGrid InvIT).
    * Real-time data fetching via Yahoo Finance API with intelligent caching to prevent rate limits.
* ** Privacy-First:**
    * **Zero-Database:** All data is processed locally in RAM (Session State).
    * **No Storage:** Closing the tab wipes all portfolio data instantly.

### Tech Stack
* **Frontend:** Streamlit
* **Financial Data:** yfinance (Yahoo Finance API)
* **Data Processing:** Pandas & NumPy
* **Caching:** Streamlit Native Caching (TTL)

###  How to Run Locally

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/yourusername/Data-Analytics-Portfolio.git](https://github.com/yourusername/Data-Analytics-Portfolio.git)
    ```
2.  **Install dependencies:**
    ```bash
    pip install streamlit yfinance pandas
    ```
3.  **Run the app:**
    ```bash
    streamlit run app.py
    ```

---
*Disclaimer: This tool is for estimation purposes only. Please verify all data with your Form 26AS.*
Linkedin: https://www.linkedin.com/in/kevin-joseph-in/
