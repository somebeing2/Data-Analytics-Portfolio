import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date
import time
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="DiviTrack Pro", layout="wide", page_icon="💸")

# --- 2. UTILITY FUNCTIONS (THE BRAIN) ---

def get_fy(d: date) -> str:
    """Return Strict Financial Year (e.g., FY23-24)"""
    if d.month >= 4:
        return f"FY{d.year % 100}-{(d.year + 1) % 100}"
    else:
        return f"FY{(d.year - 1) % 100}-{d.year % 100}"

def get_cy(d: date) -> str:
    """Return Calendar Year (e.g., 2024)"""
    return str(d.year)

def get_quarter(d: date, is_fy_view: bool) -> str:
    """Return Quarter Tag based on View Mode"""
    m = d.month
    if is_fy_view:
        # Fiscal Quarters (Apr-Jun = Q1)
        if m >= 4: return f"Q{(m - 4) // 3 + 1}"
        else: return "Q4"
    else:
        # Calendar Quarters (Jan-Mar = Q1)
        return f"Q{(m - 1) // 3 + 1}"

# --- 3. DATA LOADER ---
@st.cache_data
def load_stock_list():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, "EQUITY_L.csv")
        df = pd.read_csv(csv_path, on_bad_lines='skip')
        df.columns = [c.strip() for c in df.columns]
        
        # Add REITs
        reits = [
            {"NAME OF COMPANY": "Embassy REIT", "SYMBOL": "EMBASSY"},
            {"NAME OF COMPANY": "Mindspace REIT", "SYMBOL": "MINDSPACE"},
            {"NAME OF COMPANY": "Brookfield REIT", "SYMBOL": "BIRET"},
            {"NAME OF COMPANY": "Nexus Select Trust", "SYMBOL": "NEXUS"},
            {"NAME OF COMPANY": "India Grid Trust", "SYMBOL": "INDIAGRID"},
            {"NAME OF COMPANY": "PowerGrid InvIT", "SYMBOL": "PGINVIT"},
            {"NAME OF COMPANY": "IRB InvIT", "SYMBOL": "IRBINVIT"}
        ]
        df = pd.concat([df, pd.DataFrame(reits)], ignore_index=True)
        df['Label'] = df['NAME OF COMPANY'] + " (" + df['SYMBOL'] + ")"
        return df
    except:
        return pd.DataFrame()

# --- 4. SESSION STATE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []

# --- 5. SIDEBAR ---
st.sidebar.title("💸 DiviTrack Pro")

# RESET BUTTON (CRITICAL FOR FIXING BUGS)
if st.sidebar.button("↻ Reset App State"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
with st.sidebar.expander("➕ Add Stock", expanded=True):
    stock_df = load_stock_list()
    with st.form("add_stock"):
        if not stock_df.empty:
            sel = st.selectbox("Search", stock_df['Label'], index=None)
            ticker = f"{sel.split('(')[-1].replace(')', '').strip()}.NS" if sel else None
            name = sel.split("(")[0].strip() if sel else None
        else:
            ticker = st.text_input("Symbol (e.g. ITC.NS)")
            name = ticker
            
        qty = st.number_input("Qty", 1, 100000, 100)
        buy_date = st.date_input("Buy Date", date(2023, 1, 1))
        
        if st.form_submit_button("Add"):
            if ticker:
                st.session_state.portfolio.append({
                    "Ticker": ticker, "Name": name, "Qty": qty, "BuyDate": buy_date
                })
                st.rerun()

if st.session_state.portfolio:
    st.sidebar.markdown("### Portfolio")
    for p in st.session_state.portfolio:
        st.sidebar.text(f"{p['Name'][:15]}.. ({p['Qty']})")
    if st.sidebar.button("🗑️ Clear All"):
        st.session_state.portfolio = []
        st.rerun()

# --- 6. MAIN ENGINE (RE-ENGINEERED) ---
st.title("Dividend Tax Auditor")

# A. VIEW SETTINGS
col1, col2 = st.columns(2)
with col1:
    tax_slab = st.selectbox("Tax Slab", [0, 10, 20, 30], index=3, format_func=lambda x: f"{x}%")
with col2:
    # THE VIEW TOGGLE
    view_mode = st.radio("Group By:", ["Calendar Year (Jan-Dec)", "Financial Year (Apr-Mar)"], horizontal=True)
    is_fy_view = (view_mode == "Financial Year (Apr-Mar)")

if st.session_state.portfolio:
    # B. FETCH DATA
    raw_data = []
    
    for item in st.session_state.portfolio:
        try:
            stock = yf.Ticker(item['Ticker'])
            hist = stock.dividends
            hist.index = hist.index.tz_localize(None)
            valid_divs = hist[hist.index > pd.to_datetime(item['BuyDate'])]
            
            for d, amt in valid_divs.items():
                d_date = d.date()
                # Calculate BOTH tags for every row
                row_fy = get_fy(d_date)
                row_cy = get_cy(d_date)
                
                raw_data.append({
                    "Date": d_date,
                    "Stock": item['Name'],
                    "Symbol": item['Ticker'],
                    "Qty": item['Qty'],
                    "Amount": amt,
                    "Total": round(amt * item['Qty'], 2),
                    "FY": row_fy,  # Use for TDS Calc
                    "CY": row_cy   # Use for Display
                })
        except:
            pass

    if raw_data:
        df = pd.DataFrame(raw_data)

        # C. TDS PRE-CALCULATION (Global Logic)
        # 1. Group by Stock + FY to find totals
        fy_groups = df.groupby(['Symbol', 'FY'])['Total'].sum().reset_index()
        
        # 2. Identify Taxable Pairs (Total > 5000)
        taxable_pairs = set()
        for _, row in fy_groups.iterrows():
            if row['Total'] > 5000:
                taxable_pairs.add((row['Symbol'], row['FY']))
        
        # 3. Stamp TDS on every row individually based on ITS fiscal year
        def calculate_row_tds(row):
            if (row['Symbol'], row['FY']) in taxable_pairs:
                return row['Total'] * 0.10
            return 0.0
            
        df['TDS_Amount'] = df.apply(calculate_row_tds, axis=1)

        # D. VIEW PREPARATION
        # Create a "Display_Year" column based on the user's toggle
        df['Display_Year'] = df['FY'] if is_fy_view else df['CY']
        df['Display_Quarter'] = df['Date'].apply(lambda x: get_quarter(x, is_fy_view))

        # E. DYNAMIC FILTERS
        # Get list of years available in the VIEW mode
        available_years = sorted(df['Display_Year'].unique(), reverse=True)
        
        st.markdown("### 🔎 Filters")
        c_f1, c_f2 = st.columns(2)
        
        with c_f1:
            # Force Default to Index 0 (Most Recent Year)
            # This solves "Showing all previous years" bug
            sel_year = st.selectbox("Select Year", available_years, index=0)
            
        with c_f2:
            # Filter quarters available in that specific year
            qs_in_year = sorted(df[df['Display_Year'] == sel_year]['Display_Quarter'].unique())
            qs_in_year.insert(0, "All Quarters")
            sel_q = st.selectbox("Select Quarter", qs_in_year)

        # F. APPLY FILTERS
        view_df = df[df['Display_Year'] == sel_year].copy()
        
        if sel_q != "All Quarters":
            view_df = view_df[view_df['Display_Quarter'] == sel_q]

        # G. METRICS (On Filtered Data)
        if not view_df.empty:
            total_inc = view_df['Total'].sum()
            total_tds = view_df['TDS_Amount'].sum()
            tax_val = total_inc * (tax_slab / 100)
            net = total_inc - tax_val

            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 Total Dividend", f"₹{total_inc:,.2f}", f"in {sel_year}")
            m2.metric("✂️ TDS Deducted", f"₹{total_tds:,.2f}", "Auto (>5k Rule)")
            m3.metric("🏛️ Tax Liability", f"₹{tax_val:,.2f}", f"{tax_slab}% Slab")
            m4.metric("🟢 Net Profit", f"₹{net:,.2f}", "Real In-Hand")

            # H. CHARTS & LEDGER
            st.subheader("Monthly Breakdown")
            view_df['Month'] = pd.to_datetime(view_df['Date']).dt.strftime('%b')
            months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
            chart_data = view_df.groupby('Month')['Total'].sum().reindex(months).fillna(0)
            st.bar_chart(chart_data, color="#00C853")

            with st.expander("📝 Transaction Ledger", expanded=True):
                show_cols = ['Date', 'Stock', 'Total', 'TDS_Amount', 'Display_Quarter', 'FY']
                st.dataframe(view_df[show_cols].sort_values("Date", ascending=False), use_container_width=True)

        else:
            st.warning(f"No data found for {sel_year} ({sel_q})")
            
else:
    st.info("👈 Add a stock to begin.")

# --- FOOTER ---
st.markdown("---")
st.markdown("© 2026 | Built by **[Kevin Joseph](https://www.linkedin.com/in/kevin-joseph-in/)**")
