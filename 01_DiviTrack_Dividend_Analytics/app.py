import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date
import time
import os

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="DiviTrack Pro", layout="wide", page_icon="💸")

# --- 2. HELPER FUNCTIONS ---
def get_financial_year(d):
    """STRICT Financial Year for Tax Logic (e.g., FY23-24)"""
    if d.month >= 4:
        return f"FY{d.year % 100}-{(d.year + 1) % 100}"
    else:
        return f"FY{(d.year - 1) % 100}-{d.year % 100}"

def get_calendar_year(d):
    """Calendar Year for Display (e.g., 2024)"""
    return str(d.year)

def get_quarter(d, is_fy_view):
    """Returns Quarter based on View Mode"""
    m = d.month
    if not is_fy_view:
        # Calendar: Q1 = Jan-Mar
        return f"Q{(m - 1) // 3 + 1}"
    else:
        # Fiscal: Q1 = Apr-Jun
        if m >= 4:
            return f"Q{(m - 4) // 3 + 1}"
        else:
            return "Q4"

@st.cache_data
def load_stock_map():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "EQUITY_L.csv")
    try:
        df = pd.read_csv(csv_path, on_bad_lines='skip')
        df.columns = [c.strip() for c in df.columns]
        reits_data = [
            {"NAME OF COMPANY": "Embassy Office Parks REIT", "SYMBOL": "EMBASSY"},
            {"NAME OF COMPANY": "Mindspace Business Parks REIT", "SYMBOL": "MINDSPACE"},
            {"NAME OF COMPANY": "Brookfield India Real Estate Trust", "SYMBOL": "BIRET"},
            {"NAME OF COMPANY": "Nexus Select Trust", "SYMBOL": "NEXUS"},
            {"NAME OF COMPANY": "India Grid Trust", "SYMBOL": "INDIAGRID"},
            {"NAME OF COMPANY": "PowerGrid InvIT", "SYMBOL": "PGINVIT"},
            {"NAME OF COMPANY": "IRB InvIT Fund", "SYMBOL": "IRBINVIT"}
        ]
        df = pd.concat([df, pd.DataFrame(reits_data)], ignore_index=True)
        df['Search_Label'] = df['NAME OF COMPANY'] + " (" + df['SYMBOL'] + ")"
        return df
    except:
        return pd.DataFrame()

stock_map_df = load_stock_map()

# --- 3. SESSION STATE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []

# --- 4. SIDEBAR ---
st.sidebar.header("📂 Portfolio Manager")

# Add Stock
with st.sidebar.expander("➕ Add Stock", expanded=True):
    with st.form("add_stock"):
        if not stock_map_df.empty:
            user_sel = st.selectbox("Search Stock", stock_map_df['Search_Label'], index=None, placeholder="Type name...")
            ticker_val = f"{user_sel.split('(')[-1].replace(')', '').strip()}.NS" if user_sel else None
            name_val = user_sel.split("(")[0].strip() if user_sel else None
        else:
            ticker_val = st.text_input("Symbol (e.g., ITC.NS)")
            name_val = ticker_val

        qty = st.number_input("Qty", 1, 100000, 100)
        buy_date = st.date_input("Purchase Date", date(2023, 1, 1))
        
        if st.form_submit_button("Add"):
            if ticker_val:
                st.session_state.portfolio.append({"Ticker": ticker_val, "Name": name_val, "Qty": qty, "BuyDate": buy_date})
                st.rerun()

# List Portfolio
if st.session_state.portfolio:
    st.sidebar.markdown("---")
    st.sidebar.subheader("My Holdings")
    for p in st.session_state.portfolio:
        st.sidebar.text(f"{p['Name'][:15]}.. : {p['Qty']}")
    
    if st.sidebar.button("🗑️ Clear All"):
        st.session_state.portfolio = []
        st.rerun()

# --- 5. MAIN DASHBOARD ---
st.title("💸 DiviTrack Pro")

# --- A. VIEW SETTINGS ---
st.markdown("### ⚙️ View Settings")
col_s1, col_s2, col_s3, col_s4 = st.columns(4)

with col_s1:
    tax_slab = st.selectbox("Tax Slab", [0, 10, 20, 30], index=3, format_func=lambda x: f"{x}% Slab")

with col_s2:
    # 1. VIEW MODE TOGGLE
    view_mode = st.radio("Group By:", ["Calendar Year (Jan-Dec)", "Financial Year (Apr-Mar)"], horizontal=True)
    is_fy_view = True if "Financial" in view_mode else False

# --- B. CORE DATA PROCESSING ---
if st.session_state.portfolio:
    all_data = []
    
    # 1. FETCH & PROCESS
    for item in st.session_state.portfolio:
        try:
            stock = yf.Ticker(item['Ticker'])
            divs = stock.dividends
            divs.index = divs.index.tz_localize(None)
            my_divs = divs[divs.index > pd.to_datetime(item['BuyDate'])]
            
            for d, amt in my_divs.items():
                # STRICT TAX COLUMNS (Background Logic)
                strict_fy = get_financial_year(d)
                
                # DISPLAY COLUMNS (User View Logic)
                display_year = strict_fy if is_fy_view else get_calendar_year(d)
                display_q = get_quarter(d, is_fy_view)
                
                all_data.append({
                    "Stock": item['Name'],
                    "Symbol": item['Ticker'],
                    "Date": d.date(),
                    "Amount": amt,
                    "Qty": item['Qty'],
                    "Total": round(amt * item['Qty'], 2),
                    "Strict_FY": strict_fy,       # FOR COMPLIANCE (Hidden)
                    "Display_Year": display_year, # FOR VIEWING (Visible)
                    "Display_Q": display_q
                })
        except:
            pass
            
    if all_data:
        df = pd.DataFrame(all_data)

        # --- C. TDS COMPLIANCE ENGINE (CRITICAL FIX) ---
        # Logic: TDS is calculated based on STRICT_FY sums, regardless of what the user is "viewing"
        # 1. Calculate Annual Totals per Company per FY
        fy_sums = df.groupby(['Symbol', 'Strict_FY'])['Total'].sum().reset_index()
        fy_sums.rename(columns={'Total': 'FY_Total'}, inplace=True)
        
        # 2. Merge back to main DF
        df = pd.merge(df, fy_sums, on=['Symbol', 'Strict_FY'], how='left')
        
        # 3. Apply TDS Flag: Only True if that FY's total > 5000
        df['TDS_Applicable'] = df['FY_Total'] > 5000
        
        # 4. Calculate TDS Amount (10% of row amount IF applicable)
        df['TDS_Amount'] = df.apply(lambda x: x['Total'] * 0.10 if x['TDS_Applicable'] else 0, axis=1)

        # --- D. DYNAMIC FILTERS ---
        # Get unique years from the DISPLAY column
        available_years = sorted(df['Display_Year'].unique(), reverse=True)
        
        # DEFAULT SELECTION: Pick the most recent year, NOT "All Time"
        default_idx = 0 if len(available_years) > 0 else None
        
        with col_s3:
            # Added "All Time" as an option, but default is Index 0 (Recent Year)
            options = ["All Time"] + available_years
            # Set default to index 1 (the first year) if exists, else "All Time"
            sel_idx = 1 if len(available_years) > 0 else 0
            selected_year = st.selectbox("Select Year", options, index=sel_idx)

        with col_s4:
            if selected_year != "All Time":
                qs = sorted(df[df['Display_Year'] == selected_year]['Display_Q'].unique())
                qs.insert(0, "All Quarters")
                selected_quarter = st.selectbox("Select Quarter", qs)
            else:
                selected_quarter = "All Quarters"
                st.selectbox("Select Quarter", ["All Quarters"], disabled=True)

        # --- E. FILTERING THE VIEW ---
        view_df = df.copy()
        
        # Filter Year
        if selected_year != "All Time":
            view_df = view_df[view_df['Display_Year'] == selected_year]
            
        # Filter Quarter
        if selected_quarter != "All Quarters":
            view_df = view_df[view_df['Display_Q'] == selected_quarter]

        # --- F. METRICS & DASHBOARD ---
        if not view_df.empty:
            total_gross = view_df['Total'].sum()
            total_tds = view_df['TDS_Amount'].sum() # Uses the pre-calculated correct TDS
            tax_liability = total_gross * (tax_slab/100)
            net_profit = total_gross - tax_liability
            
            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 Total Dividend", f"₹{total_gross:,.2f}", f"{selected_year}")
            m2.metric("✂️ TDS Deducted", f"₹{total_tds:,.2f}", "Auto-calculated (>₹5k/FY)")
            m3.metric("🏛️ Tax Liability", f"₹{tax_liability:,.2f}", f"{tax_slab}% Slab")
            m4.metric("🟢 Net In-Hand", f"₹{net_profit:,.2f}", "Post-Tax")
            
            # VISUALS
            c1, c2 = st.columns([2,1])
            with c1:
                st.subheader("Monthly Trend")
                view_df['Month'] = pd.to_datetime(view_df['Date']).dt.strftime('%b')
                # Sort months naturally
                order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
                chart_data = view_df.groupby('Month')['Total'].sum().reindex(order).fillna(0)
                st.bar_chart(chart_data, color="#00C853")
                
            with c2:
                st.subheader("Top Payers")
                st.dataframe(
                    view_df.groupby('Stock')['Total'].sum().sort_values(ascending=False),
                    use_container_width=True
                )
                
            # LEDGER
            with st.expander("📝 Transaction Ledger", expanded=True):
                # Clean up columns for display
                display_cols = ['Date', 'Stock', 'Amount', 'Qty', 'Total', 'Display_Q', 'Display_Year', 'TDS_Amount']
                st.dataframe(
                    view_df[display_cols].sort_values(by="Date", ascending=False),
                    use_container_width=True
                )
        else:
            st.warning(f"No dividends found for {selected_year}.")
            
else:
    st.info("👈 Add stocks in the sidebar to begin.")

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "© 2026 | Built by **[Kevin Joseph](https://www.linkedin.com/in/kevin-joseph-in/)** | "
    "Powered by [Yahoo Finance](https://pypi.org/project/yfinance/)")
