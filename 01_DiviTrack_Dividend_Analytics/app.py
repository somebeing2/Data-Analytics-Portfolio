import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import date
import time
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="DiviTrack", layout="wide", page_icon="📈")

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

# --- 3. DATA LOADING (DROPDOWN SUPPORT) ---
@st.cache_data
def load_stock_db():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, "EQUITY_L.csv")
        # Check if file exists to avoid crashing
        if not os.path.exists(csv_path):
            return pd.DataFrame()
            
        df = pd.read_csv(csv_path, on_bad_lines='skip')
        df.columns = [c.strip() for c in df.columns]
        
        # Add REITs & InvITs Manually
        extras = [
            {"NAME OF COMPANY": "Embassy Office Parks REIT", "SYMBOL": "EMBASSY"},
            {"NAME OF COMPANY": "Mindspace Business Parks REIT", "SYMBOL": "MINDSPACE"},
            {"NAME OF COMPANY": "Brookfield India Real Estate Trust", "SYMBOL": "BIRET"},
            {"NAME OF COMPANY": "Nexus Select Trust", "SYMBOL": "NEXUS"},
            {"NAME OF COMPANY": "India Grid Trust", "SYMBOL": "INDIAGRID"},
            {"NAME OF COMPANY": "PowerGrid InvIT", "SYMBOL": "PGINVIT"},
            {"NAME OF COMPANY": "IRB InvIT Fund", "SYMBOL": "IRBINVIT"}
        ]
        df = pd.concat([df, pd.DataFrame(extras)], ignore_index=True)
        
        # Create Search Label
        df['Label'] = df['NAME OF COMPANY'] + " (" + df['SYMBOL'] + ")"
        return df
    except:
        return pd.DataFrame()

# --- 4. CACHED DATA FETCHING ---
@st.cache_data(ttl=3600, show_spinner=True) 
def fetch_portfolio_data(portfolio):
    all_rows = []
    for p in portfolio:
        try:
            time.sleep(0.2) # Prevent Rate Limiting
            tk = yf.Ticker(p['Ticker'])
            hist = tk.dividends
            if not hist.empty:
                hist.index = hist.index.tz_localize(None)
            
            my_divs = hist[hist.index > pd.to_datetime(p['BuyDate'])]
            
            for d, amt in my_divs.items():
                d_obj = d.date()
                gross = amt * p['Qty']
                
                # Tags
                fy = get_fy(d_obj)
                cy = str(d_obj.year)
                
                all_rows.append({
                    "Date": d_obj,
                    "Stock": p['Name'],
                    "Symbol": p['Ticker'],
                    "Gross": gross,
                    "FY": fy,
                    "CY": cy,
                    "Q_Fiscal": get_fiscal_quarter(d_obj),
                    "Q_Cal": f"Q{(d_obj.month-1)//3+1}"
                })
        except:
            pass
    return all_rows

# --- 5. SESSION STATE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []

# --- 6. SIDEBAR ---
st.sidebar.header("Portfolio Manager")

# A. YIELD CALCULATOR (NEW)
st.sidebar.markdown("---")
with st.sidebar.expander("🧮 Yield Calculator", expanded=False):
    st.caption("Quick check for any stock")
    calc_price = st.number_input("Share Price (₹)", value=1000.0, step=10.0)
    calc_div = st.number_input("Annual Dividend (₹)", value=50.0, step=1.0)
    
    if calc_price > 0:
        yield_val = (calc_div / calc_price) * 100
        st.metric("Dividend Yield", f"{yield_val:.2f}%")
        st.caption("Note: Yield = (Div / Price) * 100")
    else:
        st.warning("Price must be > 0")
st.sidebar.markdown("---")

# B. ADD ASSET
with st.sidebar.expander("➕ Add Asset", expanded=True):
    stock_db = load_stock_db()
    
    with st.form("add"):
        # DROPDOWN LOGIC
        if not stock_db.empty:
            sel = st.selectbox("Search Stock / REIT / InvIT", stock_db['Label'], index=None, placeholder="Type to search...")
            ticker_val = f"{sel.split('(')[-1].replace(')', '').strip()}.NS" if sel else None
            name_val = sel.split("(")[0].strip() if sel else None
        else:
            ticker_val = st.text_input("Symbol (e.g. ITC.NS)")
            name_val = ticker_val

        qty = st.number_input("Qty", 1, 100000, 100)
        b_date = st.date_input("Buy Date", date(2023, 1, 1))
        
        if st.form_submit_button("Add Asset"):
            if ticker_val:
                st.session_state.portfolio.append({
                    "Ticker": ticker_val, "Name": name_val, "Qty": qty, "BuyDate": b_date
                })
                st.cache_data.clear()
                st.rerun()

if st.sidebar.button("🗑️ Clear Portfolio"):
    st.session_state.portfolio = []
    st.cache_data.clear()
    st.rerun()

# --- 7. MAIN DASHBOARD ---
st.title("DiviTrack")

# DISCLAIMERS
with st.expander("⚠️ Important Disclaimers & Privacy", expanded=False):
    st.markdown("""
    * **Residency:** Taxation rules applied here are strictly for **Resident Individuals in India**.
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
    all_rows = fetch_portfolio_data(st.session_state.portfolio)

    if all_rows:
        df = pd.DataFrame(all_rows)

        # TDS CALCULATION
        fy_sums = df.groupby(['Symbol', 'FY'])['Gross'].sum()
        taxable_keys = fy_sums[fy_sums > 5000].index.tolist()
        df['TDS'] = df.apply(lambda x: x['Gross'] * 0.10 if (x['Symbol'], x['FY']) in taxable_keys else 0, axis=1)

        # PREPARE VIEW
        if is_fiscal:
            df['Year_Display'] = df['FY']
            df['Q_Display'] = df['Q_Fiscal']
        else:
            df['Year_Display'] = df['CY']
            df['Q_Display'] = df['Q_Cal']

        # FILTER
        years = sorted(df['Year_Display'].unique(), reverse=True)
        
        st.divider()
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            sel_year = st.selectbox("Select Year", years, index=0)
        with col_f2:
            qs = sorted(df[df['Year_Display'] == sel_year]['Q_Display'].unique())
            qs.insert(0, "All Quarters")
            sel_q = st.selectbox("Select Quarter", qs)

        # APPLY
        view_df = df[df['Year_Display'] == sel_year].copy()
        if sel_q != "All Quarters":
            view_df = view_df[view_df['Q_Display'] == sel_q]

        # METRICS
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

            # --- VISUALIZATION SECTION (NEW) ---
            st.divider()
            st.subheader("📊 Visual Analytics")
            
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                st.markdown("**💰 Income Source (Top Payers)**")
                # Group by Stock to find top payers
                stock_group = view_df.groupby("Stock")['Gross'].sum().reset_index()
                fig_bar = px.bar(
                    stock_group, 
                    x='Stock', 
                    y='Gross',
                    color='Gross',
                    color_continuous_scale='Greens',
                    labels={'Gross': 'Income (₹)'}
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            with chart_col2:
                st.markdown("**📈 Income Trend (Quarterly)**")
                # Group by Quarter to show trend
                trend_group = view_df.groupby("Q_Display")['Gross'].sum().reset_index()
                fig_line = px.line(
                    trend_group, 
                    x='Q_Display', 
                    y='Gross',
                    markers=True,
                    labels={'Gross': 'Income (₹)', 'Q_Display': 'Quarter'}
                )
                fig_line.update_traces(line_color='#4CAF50', line_width=3)
                st.plotly_chart(fig_line, use_container_width=True)

            # --- DATA TABLE ---
            st.divider()
            st.subheader("📝 Transaction Details")
            st.dataframe(view_df[['Date','Stock','Gross','TDS','Year_Display']].sort_values('Date', ascending=False), use_container_width=True)
        else:
            st.warning("No data for selection.")
    else:
        st.info("No dividends found for these dates.")
else:
    st.info("Add an asset to begin.")

st.divider()
st.markdown("© 2026 | Built by **[Kevin Joseph](https://www.linkedin.com/in/kevin-joseph-in/)**")
