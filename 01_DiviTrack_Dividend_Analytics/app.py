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
    """Returns the Financial Year (e.g., 'FY24-25')"""
    if d.month >= 4:
        return f"FY{d.year % 100}-{(d.year + 1) % 100}"
    else:
        return f"FY{(d.year - 1) % 100}-{d.year % 100}"

def get_quarter(d, is_fy):
    """Returns Quarter. 
    If Calendar Year: Q1=Jan-Mar. 
    If Financial Year: Q1=Apr-Jun.
    """
    m = d.month
    if not is_fy:
        # Calendar Year Quarters
        return f"Q{(m - 1) // 3 + 1}"
    else:
        # Financial Year Quarters (India)
        # Apr-Jun=Q1, Jul-Sep=Q2, Oct-Dec=Q3, Jan-Mar=Q4
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
        # Add REITs/InvITs manually
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

# --- 4. SIDEBAR: PORTFOLIO MANAGER ---
st.sidebar.header("📂 Portfolio Manager")

# Add Stock Form
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

# --- A. SETTINGS PANEL (TOP) ---
st.markdown("### ⚙️ View Settings")
col_s1, col_s2, col_s3, col_s4 = st.columns(4)

with col_s1:
    tax_slab = st.selectbox("Tax Slab", [0, 10, 20, 30], index=3, format_func=lambda x: f"{x}% Slab")

with col_s2:
    # THE SWITCH: Calendar vs Financial Year
    year_mode = st.radio("Year Format", ["Calendar (Jan-Dec)", "Financial (Apr-Mar)"], horizontal=True)
    is_fy = True if "Financial" in year_mode else False

# --- B. DATA PROCESSING ---
if st.session_state.portfolio:
    all_data = []
    
    # Process all stocks
    for item in st.session_state.portfolio:
        try:
            stock = yf.Ticker(item['Ticker'])
            divs = stock.dividends
            divs.index = divs.index.tz_localize(None)
            my_divs = divs[divs.index > pd.to_datetime(item['BuyDate'])]
            
            for d, amt in my_divs.items():
                fy = get_financial_year(d)
                cy = str(d.year)
                q = get_quarter(d, is_fy)
                
                all_data.append({
                    "Stock": item['Name'],
                    "Symbol": item['Ticker'],
                    "Date": d.date(),
                    "Year_Ref": fy if is_fy else cy, # This controls how data is grouped (FY vs CY)
                    "Quarter": q,
                    "Amount": amt,
                    "Qty": item['Qty'],
                    "Total": round(amt * item['Qty'], 2)
                })
        except:
            pass
            
    if all_data:
        df = pd.DataFrame(all_data)
        
        # --- C. DYNAMIC FILTERS ---
        available_years = sorted(df['Year_Ref'].unique(), reverse=True)
        available_years.insert(0, "All Time")
        
        with col_s3:
            selected_year = st.selectbox("Select Period", available_years)
            
        with col_s4:
            # Quarter Filter (Only active if a specific year is chosen)
            if selected_year != "All Time":
                qs = sorted(df[df['Year_Ref'] == selected_year]['Quarter'].unique())
                qs.insert(0, "All Quarters")
                selected_quarter = st.selectbox("Select Quarter", qs)
            else:
                selected_quarter = "All Quarters"
                st.selectbox("Select Quarter", ["All Quarters"], disabled=True)

        # --- D. FILTER LOGIC ---
        # 1. Filter by Year
        if selected_year != "All Time":
            view_df = df[df['Year_Ref'] == selected_year]
        else:
            view_df = df.copy()
            
        # 2. Filter by Quarter
        if selected_quarter != "All Quarters":
            view_df = view_df[view_df['Quarter'] == selected_quarter]

        # --- E. METRICS CALCULATION (AUTO TDS) ---
        if not view_df.empty:
            total_gross = view_df['Total'].sum()
            
            # TDS Logic:
            # 1. Group by Symbol + Year_Ref to check the 5000 limit limit GLOBALLY for that year
            # We use the full 'df' (not view_df) to check eligibility, because splitting quarters shouldn't hide TDS liability
            eligibility_df = df.groupby(['Symbol', 'Year_Ref'])['Total'].sum().reset_index()
            eligibility_df['Is_TDS'] = eligibility_df['Total'] > 5000
            
            # 2. Merge eligibility back to the VIEW dataframe
            view_df = pd.merge(view_df, eligibility_df[['Symbol', 'Year_Ref', 'Is_TDS']], on=['Symbol', 'Year_Ref'], how='left')
            
            # 3. Calculate TDS only where eligible
            view_df['TDS_Ded'] = view_df.apply(lambda x: x['Total'] * 0.10 if x['Is_TDS'] else 0, axis=1)
            
            total_tds = view_df['TDS_Ded'].sum()
            tax_liability = total_gross * (tax_slab/100)
            net_profit = total_gross - tax_liability
            
            # --- F. DISPLAY METRICS ---
            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 Total Dividend", f"₹{total_gross:,.2f}", f"{selected_year}")
            m2.metric("✂️ TDS Deducted", f"₹{total_tds:,.2f}", "Auto-calculated >5k")
            m3.metric("🏛️ Tax Liability", f"₹{tax_liability:,.2f}", f"{tax_slab}% Slab")
            m4.metric("🟢 Net In-Hand", f"₹{net_profit:,.2f}", "Post-Tax")
            
            # --- G. VISUALS ---
            c1, c2 = st.columns([2,1])
            with c1:
                st.subheader("Monthly Trend")
                view_df['Month'] = pd.to_datetime(view_df['Date']).dt.strftime('%b')
                chart_data = view_df.groupby('Month')['Total'].sum().reindex(
                    ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
                ).fillna(0)
                st.bar_chart(chart_data, color="#00C853")
                
            with c2:
                st.subheader("Top Payers")
                st.dataframe(
                    view_df.groupby('Stock')['Total'].sum().sort_values(ascending=False),
                    use_container_width=True
                )
                
            # --- H. LEDGER ---
            with st.expander("📝 View Transaction Ledger", expanded=True):
                st.dataframe(
                    view_df[['Date', 'Stock', 'Amount', 'Qty', 'Total', 'Quarter', 'Year_Ref']]
                    .sort_values(by="Date", ascending=False),
                    use_container_width=True
                )
                
        else:
            st.warning(f"No dividends found for {selected_year} ({selected_quarter})")

else:
    st.info("👈 Add stocks in the sidebar to begin.")

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "© 2026 | Built by **[Kevin Joseph](https://www.linkedin.com/in/kevin-joseph-in/)** | "
    "Powered by [Yahoo Finance](https://pypi.org/project/yfinance/)")
