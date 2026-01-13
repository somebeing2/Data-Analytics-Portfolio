import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date, datetime
import time
import os

# --- 1. CONFIGURATION & STATE ---
st.set_page_config(page_title="DiviTrack Pro", layout="wide", page_icon="💸")

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []

# --- 2. ROBUST UTILITY FUNCTIONS ---

def get_fy_tag(d: date) -> str:
    """Returns Financial Year tag (e.g., 'FY24-25')"""
    if d.month >= 4:
        return f"FY{d.year % 100}-{(d.year + 1) % 100}"
    else:
        return f"FY{(d.year - 1) % 100}-{d.year % 100}"

def get_quarter_tag(d: date, is_fy: bool) -> str:
    """Returns Quarter tag based on view mode"""
    m = d.month
    if is_fy:
        # Fiscal: Apr-Jun=Q1, Jul-Sep=Q2, Oct-Dec=Q3, Jan-Mar=Q4
        if m >= 4: return f"Q{(m - 4) // 3 + 1}"
        else: return "Q4"
    else:
        # Calendar: Jan-Mar=Q1 ...
        return f"Q{(m - 1) // 3 + 1}"

def calculate_tds_eligibility(full_df):
    """
    CRITICAL LOGIC: 
    1. Scan ALL dividend history.
    2. Group by Stock + Financial Year.
    3. If Sum > 5000, mark THAT pair as Taxable.
    """
    if full_df.empty:
        return {}
    
    # Group by Symbol and STRICT FY (Tax Law)
    fy_summary = full_df.groupby(['Symbol', 'Strict_FY'])['Total_Gross'].sum()
    
    # Create a set of "Taxable Events" (e.g., "ITC.NS_FY24-25")
    taxable_keys = set()
    for (symbol, fy), total_amt in fy_summary.items():
        if total_amt > 5000:
            taxable_keys.add(f"{symbol}_{fy}")
            
    return taxable_keys

@st.cache_data
def load_stock_master():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, "EQUITY_L.csv")
        df = pd.read_csv(csv_path, on_bad_lines='skip')
        df.columns = [c.strip() for c in df.columns]
        
        # Add REITs/InvITs manually
        extra_stocks = [
            {"NAME OF COMPANY": "Embassy Office Parks REIT", "SYMBOL": "EMBASSY"},
            {"NAME OF COMPANY": "Mindspace Business Parks REIT", "SYMBOL": "MINDSPACE"},
            {"NAME OF COMPANY": "Brookfield India Real Estate Trust", "SYMBOL": "BIRET"},
            {"NAME OF COMPANY": "Nexus Select Trust", "SYMBOL": "NEXUS"},
            {"NAME OF COMPANY": "India Grid Trust", "SYMBOL": "INDIAGRID"},
            {"NAME OF COMPANY": "PowerGrid InvIT", "SYMBOL": "PGINVIT"},
            {"NAME OF COMPANY": "IRB InvIT Fund", "SYMBOL": "IRBINVIT"}
        ]
        df = pd.concat([df, pd.DataFrame(extra_stocks)], ignore_index=True)
        df['Label'] = df['NAME OF COMPANY'] + " (" + df['SYMBOL'] + ")"
        return df
    except:
        return pd.DataFrame()

# --- 3. SIDEBAR ---
st.sidebar.title("💸 DiviTrack Pro")
st.sidebar.markdown("---")

# RESET BUTTON (Fixes Cache Issues)
if st.sidebar.button("↻ Reset / Clear Cache"):
    st.cache_data.clear()
    st.rerun()

# INPUT FORM
with st.sidebar.expander("➕ Add Stock", expanded=True):
    stock_map = load_stock_master()
    with st.form("add_stock"):
        if not stock_map.empty:
            sel = st.selectbox("Search", stock_map['Label'], index=None, placeholder="Name or Symbol...")
            ticker = f"{sel.split('(')[-1].replace(')', '').strip()}.NS" if sel else None
            name = sel.split("(")[0].strip() if sel else None
        else:
            ticker = st.text_input("Symbol (e.g. ITC.NS)")
            name = ticker
            
        qty = st.number_input("Quantity", 1, 100000, 100)
        buy_date = st.date_input("Purchase Date", date(2023, 1, 1))
        
        if st.form_submit_button("Add to Portfolio"):
            if ticker:
                st.session_state.portfolio.append({
                    "Ticker": ticker, "Name": name, "Qty": qty, "BuyDate": buy_date
                })
                st.rerun()

if st.session_state.portfolio:
    st.sidebar.markdown("### Holdings")
    for p in st.session_state.portfolio:
        st.sidebar.text(f"{p['Name'][:15]}... ({p['Qty']})")
    
    if st.sidebar.button("🗑️ Delete All"):
        st.session_state.portfolio = []
        st.rerun()

# --- 4. MAIN LOGIC ENGINE ---
st.title("Dividend Tax Auditor")

# A. VIEW SETTINGS (The "Lens")
col_view1, col_view2 = st.columns(2)
with col_view1:
    tax_slab = st.selectbox("Your Tax Slab", [0, 10, 20, 30], index=3, format_func=lambda x: f"{x}%")
with col_view2:
    view_mode = st.radio("Time View", ["Calendar Year", "Financial Year"], horizontal=True)
    is_fy_view = (view_mode == "Financial Year")

# B. DATA PROCESSING (The "Brain")
if st.session_state.portfolio:
    raw_records = []
    
    # Step 1: Fetch Raw Data
    for item in st.session_state.portfolio:
        try:
            stock = yf.Ticker(item['Ticker'])
            hist = stock.dividends
            hist.index = hist.index.tz_localize(None)
            
            # Filter: Only dividends AFTER purchase
            valid_divs = hist[hist.index > pd.to_datetime(item['BuyDate'])]
            
            for d, amt in valid_divs.items():
                d_date = d.date()
                gross = round(amt * item['Qty'], 2)
                
                # Calculate Tags
                fy_tag = get_fy_tag(d_date)             # ALWAYS calculate strict FY for Tax
                cy_tag = str(d_date.year)               # Calendar Year
                
                # Decide what "Year" to show based on user toggle
                display_year = fy_tag if is_fy_view else cy_tag
                display_q = get_quarter_tag(d_date, is_fy_view)
                
                raw_records.append({
                    "Date": d_date,
                    "Stock": item['Name'],
                    "Symbol": item['Ticker'],
                    "Qty": item['Qty'],
                    "Amount": amt,
                    "Total_Gross": gross,
                    "Strict_FY": fy_tag,       # Critical for TDS logic
                    "Display_Year": display_year, # Critical for Visualization
                    "Display_Q": display_q
                })
        except:
            pass

    if raw_records:
        df = pd.DataFrame(raw_records)
        
        # Step 2: CALCULATE TDS (The "Compliance Layer")
        # We calculate this on the FULL dataframe before filtering
        taxable_map = calculate_tds_eligibility(df)
        
        # Apply TDS Logic Row-by-Row
        def apply_tds(row):
            key = f"{row['Symbol']}_{row['Strict_FY']}"
            if key in taxable_map:
                return row['Total_Gross'] * 0.10
            return 0.0
            
        df['TDS_Amount'] = df.apply(apply_tds, axis=1)
        
        # Step 3: FILTERING (The "Presentation Layer")
        
        # Defaults: Find the "Current" period to show
        all_years = sorted(df['Display_Year'].unique(), reverse=True)
        
        # Top Filter Bar
        st.markdown("### 🔎 Period Filter")
        c_f1, c_f2 = st.columns(2)
        
        with c_f1:
            # Default to the most recent
