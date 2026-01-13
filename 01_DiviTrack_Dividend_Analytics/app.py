import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="DiviTrack Pro", layout="wide", page_icon="💸")

# --- 2. LOGIC CORE (The "Brain") ---
def get_fy(d):
    """Return Strict Financial Year (e.g., 'FY24-25')"""
    return f"FY{d.year % 100}-{(d.year + 1) % 100}" if d.month >= 4 else f"FY{(d.year - 1) % 100}-{d.year % 100}"

def get_cy(d):
    """Return Strict Calendar Year (e.g., '2024')"""
    return str(d.year)

def get_fiscal_quarter(d):
    """Return Fiscal Quarter (Apr-Jun = Q1)"""
    if d.month >= 4: return f"Q{(d.month - 4) // 3 + 1}"
    return "Q4"

def get_cal_quarter(d):
    """Return Calendar Quarter (Jan-Mar = Q1)"""
    return f"Q{(d.month - 1) // 3 + 1}"

@st.cache_data
def load_stock_db():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, "EQUITY_L.csv")
        df = pd.read_csv(csv_path, on_bad_lines='skip')
        df.columns = [c.strip() for c in df.columns]
        # Add REITs
        extras = [{"NAME OF COMPANY": "Embassy REIT", "SYMBOL": "EMBASSY"},
                  {"NAME OF COMPANY": "Mindspace REIT", "SYMBOL": "MINDSPACE"},
                  {"NAME OF COMPANY": "PowerGrid InvIT", "SYMBOL": "PGINVIT"},
                  {"NAME OF COMPANY": "India Grid Trust", "SYMBOL": "INDIAGRID"}]
        df = pd.concat([df, pd.DataFrame(extras)], ignore_index=True)
        df['Label'] = df['NAME OF COMPANY'] + " (" + df['SYMBOL'] + ")"
        return df
    except:
        return pd.DataFrame()

# --- 3. SESSION STATE & SIDEBAR ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []

st.sidebar.title("💸 DiviTrack Pro")

# NUCLEAR RESET BUTTON (Fixes the "Stuck Data" bug)
if st.sidebar.button("↻ RESET APP", type="primary"):
    st.cache_data.clear()
    st.rerun()

# STOCK ADDER
with st.sidebar.expander("➕ Add Stock", expanded=True):
    db = load_stock_db()
    with st.form("add"):
        sel = st.selectbox("Search", db['Label'], index=None) if not db.empty else None
        ticker_in = st.text_input("Or Symbol (ITC.NS)")
        
        final_ticker = f"{sel.split('(')[-1].replace(')', '').strip()}.NS" if sel else (ticker_in if ticker_in else None)
        final_name = sel.split("(")[0].strip() if sel else ticker_in
        
        qty = st.number_input("Qty", 1, 100000, 100)
        b_date = st.date_input("Buy Date", date(2023, 1, 1))
        
        if st.form_submit_button("Add"):
            if final_ticker:
                st.session_state.portfolio.append({"Ticker": final_ticker, "Name": final_name, "Qty": qty, "BuyDate": b_date})
                st.rerun()

if st.session_state.portfolio:
    st.sidebar.divider()
    st.sidebar.write(f"**Holdings:** {len(st.session_state.portfolio)}")
    if st.sidebar.button("🗑️ Delete All"):
        st.session_state.portfolio = []
        st.rerun()

# --- 4. MAIN DASHBOARD ---
st.title("Dividend Tax Auditor")

# VIEW SETTINGS
c1, c2 = st.columns(2)
with c1:
    tax_slab = st.selectbox("Tax Slab", [0, 10, 20, 30], index=3, format_func=lambda x: f"{x}%")
with c2:
    view_mode = st.radio("View Mode", ["Calendar (Jan-Dec)", "Fiscal (Apr-Mar)"], horizontal=True)
    is_fiscal = "Fiscal" in view_mode

if st.session_state.portfolio:
    # --- STEP A: BUILD MASTER DATAFRAME ---
    all_rows = []
    
    for p in st.session_state.portfolio:
        try:
            # 1. Fetch
            tk = yf.Ticker(p['Ticker'])
            hist = tk.dividends
            hist.index = hist.index.tz_localize(None)
            
            # 2. Filter by Buy Date
            my_divs = hist[hist.index > pd.to_datetime(p['BuyDate'])]
            
            for d, amt in my_divs.items():
                d_obj = d.date()
                gross = amt * p['Qty']
                
                # 3. Pre-Calculate ALL Tags
                all_rows.append({
                    "Date": d_obj,
                    "Stock": p['Name'],
                    "Symbol": p['Ticker'],
                    "Gross": round(gross, 2),
                    "FY": get_fy(d_obj),       # For TDS Logic (Always Fiscal)
                    "CY": get_cy(d_obj),       # For Calendar View
                    "Q_Fiscal": get_fiscal_quarter(d_obj),
                    "Q_Cal": get_cal_quarter(d_obj)
                })
        except:
            pass

    if all_rows:
        df = pd.DataFrame(all_rows)

        # --- STEP B: GLOBAL TDS CALCULATION (Fixes Auto-TDS Bug) ---
        # 1. Group by [Stock + Fiscal Year] to find Total Annual Income
        fy_grouped = df.groupby(['Symbol', 'FY'])['Gross'].sum()
        
        # 2. Identify "Taxable Buckets" (>5000)
        taxable_keys = fy_grouped[fy_grouped > 5000].index.tolist() # List of (Symbol, FY) tuples
        
        # 3. Apply TDS to individual rows if they belong to a Taxable Bucket
        # (This works regardless of what view/year you select later)
        def calc_tds(row):
            if (row['Symbol'], row['FY']) in taxable_keys:
                return row['Gross'] * 0.10
            return 0.0
        
        df['TDS'] = df.apply(calc_tds, axis=1)

        # --- STEP C: PREPARE VIEW (Fixes View Switching Bug) ---
        # Create 'Display' columns based on user toggle
        if is_fiscal:
            df['View_Year'] = df['FY']
            df['View_Q'] = df['Q_Fiscal']
        else:
            df['View_Year'] = df['CY']
            df['View_Q'] = df['Q_Cal']

        # --- STEP D: FILTERING (Fixes "Showing All Years" Bug) ---
        # 1. Get unique years from the VIEW column
        years_list = sorted(df['View_Year'].unique(), reverse=True)
        
        st.divider()
        fc1, fc2 = st.columns(2)
        with fc1:
            # Default to index 0 (Most Recent Year)
            sel_year = st.selectbox("Select Year", years_list, index=0)
        with fc2:
            # Get quarters valid for THIS selected year
            qs_list = sorted(df[df['View_Year'] == sel_year]['View_Q'].unique())
            qs_list.insert(0, "All Quarters")
            sel_q = st.selectbox("Select Quarter", qs_list)

        # 2. Apply Slice
        view_df = df[df['View_Year'] == sel_year].copy()
        if sel_q != "All Quarters":
            view_df = view_df[view_df['View_Q'] == sel_q]

        # --- STEP E: SHOW RESULTS ---
        if not view_df.empty:
            tot_gross = view_df['Gross'].sum()
            tot_tds = view_df['TDS'].sum()
            tax_amt = tot_gross * (tax_slab / 100)
            net = tot_gross - tax_amt

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Dividend", f"₹{tot_gross:,.2f}", f"in {sel_year}")
            m2.metric("TDS Deducted", f"₹{tot_tds:,.2f}", "Auto (>5k Rule)")
            m3.metric("Tax Liability", f"₹{tax_amt:,.2f}", f"{tax_slab}% Slab")
            m4.metric("Net Profit", f"₹{net:,.2f}", "In Hand")

            # Chart
            st.caption("Monthly Trend")
            view_df['Month'] = pd.to_datetime(view_df['Date']).dt.strftime('%b')
            chart_data = view_df.groupby('Month')['Gross'].sum()
            st.bar_chart(chart_data, color="#00C853")

            # Ledger
            with st.expander("Show Transaction Ledger", expanded=True):
                st.dataframe(
                    view_df[['Date', 'Stock', 'Gross', 'TDS', 'View_Q', 'View_Year']].sort_values("Date", ascending=False),
                    use_container_width=True
                )
        else:
            st.warning("No data for this period.")

    else:
        st.info("No dividends found for these stocks.")
else:
    st.info("👈 Add a stock to begin.")

# --- FOOTER ---
st.divider()
st.markdown("© 2026 | Built by **[Kevin Joseph](https://www.linkedin.com/in/kevin-joseph-in/)**")
