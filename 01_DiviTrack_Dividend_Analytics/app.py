import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date
import time
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="DiviTrack Pro", layout="wide", page_icon="📈")

# --- 2. LOGIC FUNCTIONS ---
def get_fy(d):
    """Return Strict Financial Year (e.g., 'FY24-25')"""
    if d.month >= 4:
        return f"FY{d.year % 100}-{(d.year + 1) % 100}"
    else:
        return f"FY{(d.year - 1) % 100}-{d.year % 100}"

def get_fiscal_quarter(d):
    """Return Fiscal Quarter (Apr-Jun = Q1)"""
    if d.month >= 4: return f"Q{(d.month - 4) // 3 + 1}"
    return "Q4"

# --- 3. CACHED DATA FETCHING (FIXES RATE LIMIT ERROR) ---
@st.cache_data(ttl=3600, show_spinner=True) 
def fetch_portfolio_data(portfolio):
    """
    Fetches data for the entire portfolio once and caches it.
    This prevents hitting Yahoo Finance limits when changing views.
    """
    all_rows = []
    
    for p in portfolio:
        try:
            # Add small delay to prevent rate limiting
            time.sleep(0.2) 
            
            tk = yf.Ticker(p['Ticker'])
            hist = tk.dividends
            
            # Convert timezone if needed
            if not hist.empty:
                hist.index = hist.index.tz_localize(None)
            
            # Filter by Buy Date
            my_divs = hist[hist.index > pd.to_datetime(p['BuyDate'])]
            
            for d, amt in my_divs.items():
                d_obj = d.date()
                gross = amt * p['Qty']
                
                # Pre-calculate Tags
                fy = get_fy(d_obj)      # Fiscal (FY24-25)
                cy = str(d_obj.year)    # Calendar (2024)
                
                all_rows.append({
                    "Date": d_obj,
                    "Stock": p['Name'],
                    "Symbol": p['Ticker'],
                    "Gross": gross,
                    "FY": fy,
                    "CY": cy,
                    # We store both quarter types so we can switch instantly
                    "Q_Fiscal": get_fiscal_quarter(d_obj),
                    "Q_Cal": f"Q{(d_obj.month-1)//3+1}"
                })
        except Exception as e:
            # Log error but don't crash app
            print(f"Error fetching {p['Ticker']}: {e}")
            pass
            
    return all_rows

# --- 4. SESSION STATE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []

# --- 5. SIDEBAR: PORTFOLIO MANAGER ---
st.sidebar.header("Portfolio Manager")

# STOCK ADDER
with st.sidebar.expander("➕ Add Stock", expanded=True):
    with st.form("add"):
        ticker_in = st.text_input("Stock Symbol", "ITC.NS")
        qty = st.number_input("Qty", 1, 100000, 100)
        b_date = st.date_input("Buy Date", date(2023, 1, 1))
        
        if st.form_submit_button("Add Stock"):
            try:
                # Quick check to get a better name if possible
                t = yf.Ticker(ticker_in)
                name = t.info.get('shortName', ticker_in)
            except:
                name = ticker_in
            
            st.session_state.portfolio.append({
                "Ticker": ticker_in, "Name": name, "Qty": qty, "BuyDate": b_date
            })
            # Clear cache so new stock is fetched
            st.cache_data.clear()
            st.rerun()

if st.sidebar.button("🗑️ Clear Portfolio"):
    st.session_state.portfolio = []
    st.cache_data.clear()
    st.rerun()

# --- 6. MAIN DASHBOARD ---
st.title("DiviTrack Pro")

# --- DISCLAIMERS ---
with st.expander("⚠️ Important Disclaimers & Privacy", expanded=False):
    st.markdown("""
    * **Not Financial Advice:** This tool is for estimation only.
    * **Verify Data:** Dividend data is fetched from Yahoo Finance APIs. Verify with your Form 26AS.
    * **Tax Rules:** TDS calculations are estimates (10%) and do not account for specific exemptions.
    * **🔒 Privacy Notice:** Your data is processed locally in RAM. It is never stored, saved, or shared. Refreshing this page wipes all data.
    """)

# VIEW SETTINGS
c1, c2 = st.columns(2)
with c1:
    tax_slab = st.selectbox("Tax Slab", [0, 10, 20, 30], index=3)
with c2:
    view_mode = st.radio("Group By", ["Calendar Year", "Financial Year"], horizontal=True)
    is_fiscal = "Financial" in view_mode

if st.session_state.portfolio:
    
    # FETCH DATA (Cached)
    all_rows = fetch_portfolio_data(st.session_state.portfolio)

    if all_rows:
        df = pd.DataFrame(all_rows)

        # --- TDS CALCULATION (FY BASED) ---
        # 1. Sum by FY to find >5000 (Always use FY for tax rules)
        fy_sums = df.groupby(['Symbol', 'FY'])['Gross'].sum()
        taxable_keys = fy_sums[fy_sums > 5000].index.tolist()
        
        # 2. Stamp TDS
        df['TDS'] = df.apply(lambda x: x['Gross'] * 0.10 if (x['Symbol'], x['FY']) in taxable_keys else 0, axis=1)

        # --- PREPARE VIEW COLUMNS ---
        if is_fiscal:
            df['Year_Display'] = df['FY']
            df['Q_Display'] = df['Q_Fiscal']
        else:
            df['Year_Display'] = df['CY']
            df['Q_Display'] = df['Q_Cal']

        # --- FILTERING ---
        years = sorted(df['Year_Display'].unique(), reverse=True)
        
        st.divider()
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            sel_year = st.selectbox("Select Year", years, index=0) # Auto-select most recent
        with col_f2:
            qs = sorted(df[df['Year_Display'] == sel_year]['Q_Display'].unique())
            qs.insert(0, "All Quarters")
            sel_q = st.selectbox("Select Quarter", qs)

        # APPLY FILTER
        view_df = df[df['Year_Display'] == sel_year].copy()
        if sel_q != "All Quarters":
            view_df = view_df[view_df['Q_Display'] == sel_q]

        # --- DISPLAY ---
        if not view_df.empty:
            tot = view_df['Gross'].sum()
            tds = view_df['TDS'].sum()
            tax = tot * (tax_slab/100)
            net = tot - tax

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Dividend", f"₹{tot:,.2f}")
            m2.metric("TDS Deducted", f"₹{tds:,.2f}")
            m3.metric("Tax Liability", f"₹{tax:,.2f}")
            m4.metric("Net In-Hand", f"₹{net:,.2f}")

            st.dataframe(view_df[['Date','Stock','Gross','TDS','Year_Display']].sort_values('Date', ascending=False), use_container_width=True)
        else:
            st.warning("No data for selection.")
    else:
        st.info("No dividends found for these dates.")
else:
    st.info("Add stock to begin.")

# --- FOOTER ---
st.divider()
st.markdown("© 2026 | Built by **[Kevin Joseph](https://www.linkedin.com/in/kevin-joseph-in/)**")
