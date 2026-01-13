import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date
import time
import os

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="DiviTrack | Dividend Auditor", layout="wide")

# --- 2. HELPER FUNCTIONS ---

def get_financial_year(d):
    """Returns the Financial Year (e.g., 'FY24-25') for a given date."""
    if d.month >= 4:
        return f"FY{d.year % 100}-{(d.year + 1) % 100}"
    else:
        return f"FY{(d.year - 1) % 100}-{d.year % 100}"

def get_quarter(d):
    """Returns the Calendar Quarter (Q1, Q2, Q3, Q4)."""
    return f"Q{(d.month - 1) // 3 + 1}"

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
            {"NAME OF COMPANY": "IRB InvIT Fund", "SYMBOL": "IRBINVIT"},
            {"NAME OF COMPANY": "Shrem InvIT", "SYMBOL": "SHREMINVIT"}
        ]
        
        df_reits = pd.DataFrame(reits_data)
        df = pd.concat([df, df_reits], ignore_index=True)
        df['Search_Label'] = df['NAME OF COMPANY'] + " (" + df['SYMBOL'] + ")"
        return df

    except FileNotFoundError:
        st.error(f"⚠ Could not find 'EQUITY_L.csv'. Code looked at: {csv_path}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"⚠ Error loading stock list: {e}")
        return pd.DataFrame()

stock_map_df = load_stock_map()

# --- 3. DISCLAIMER & PRIVACY ---
st.warning("""
    ⚠️ **IMPORTANT DISCLAIMER:**
    * **Resident Individuals Only:** TDS logic assumes you are a Resident Individual (Section 194).
    * **TDS Rule:** 10% TDS is auto-calculated ONLY if dividends from a single company exceed ₹5,000 in a Financial Year.
    * **Not Financial Advice:** Verify all data with your Form 26AS.
""")

st.success("🔒 **Privacy Notice:** Your data is processed locally in RAM. It is never stored, saved, or shared.")

# Initialize Session State
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []

# --- 4. SIDEBAR: SMART INPUTS ---
st.sidebar.header("💰 Add to Portfolio")

with st.sidebar.form("add_stock_form"):
    selected_ticker_symbol = None
    selected_stock_name = None
    
    if not stock_map_df.empty:
        user_selection = st.selectbox(
            "Search Stock Name", 
            stock_map_df['Search_Label'],
            index=None,
            placeholder="Type 'Zomato' or 'Embassy'..."
        )
        
        if user_selection:
            try:
                clean_symbol = user_selection.split("(")[-1].replace(")", "").strip()
                selected_ticker_symbol = f"{clean_symbol}.NS"
                selected_stock_name = user_selection.split("(")[0].strip()
            except:
                st.error("Error parsing name.")
            
    else:
        raw_input = st.text_input("Stock Symbol (Manual)", "ITC.NS")
        if raw_input:
            clean_symbol = raw_input.upper().replace(" ", "").strip()
            selected_ticker_symbol = clean_symbol if clean_symbol.endswith(".NS") else f"{clean_symbol}.NS"
            selected_stock_name = selected_ticker_symbol

    qty_input = st.number_input("Quantity", min_value=1, max_value=100000, value=100)
    buy_date_input = st.date_input("Purchase Date", date(2023, 1, 1))
    
    submitted = st.form_submit_button("Add Stock")
    
    if submitted:
        if selected_ticker_symbol:
            st.session_state.portfolio.append({
                "Ticker": selected_ticker_symbol,
                "Name": selected_stock_name,
                "Qty": qty_input,
                "BuyDate": buy_date_input
            })
            st.success(f"Added {selected_stock_name}")

if st.sidebar.button("🗑️ Clear Portfolio"):
    st.session_state.portfolio = []
    st.rerun()

# --- 5. MAIN LOGIC ---
st.title("💸 DiviTrack: Dividend Tax & Eligibility Calculator")

# Tax Configuration
col_tax1, col_tax2 = st.columns(2)
with col_tax1:
    tax_slab = st.selectbox("Select Your Income Tax Slab", [0, 10, 20, 30], index=3, format_func=lambda x: f"{x}% Slab")
with col_tax2:
    st.info("ℹ️ TDS is now auto-calculated per company/FY.")

# --- 6. PROCESSING ENGINE ---
if len(st.session_state.portfolio) > 0:
    st.divider()
    
    all_payouts = []
    progress_text = "Scanning secure data streams..."
    my_bar = st.progress(0, text=progress_text)
    
    total_stocks = len(st.session_state.portfolio)
    
    for i, item in enumerate(st.session_state.portfolio):
        ticker = item['Ticker']
        name = item.get('Name', ticker) 
        qty = item['Qty']
        buy_date = pd.to_datetime(item['BuyDate'])
        
        # Rate Limiting
        time.sleep(0.1) 
        my_bar.progress((i + 1) / total_stocks, text=f"Verifying {name}...")
        
        try:
            stock = yf.Ticker(ticker)
            div_history = stock.dividends
            
            if not div_history.empty:
                div_history.index = div_history.index.tz_localize(None)
                my_dividends = div_history[div_history.index > buy_date]
                
                for date_val, amount in my_dividends.items():
                    payout = amount * qty
                    # Determine Financial Year & Calendar Year
                    fy = get_financial_year(date_val)
                    cy = date_val.year
                    quarter = get_quarter(date_val)
                    
                    all_payouts.append({
                        "Stock": name,
                        "Symbol": ticker,
                        "Ex-Date": date_val.date(),
                        "Financial Year": fy,
                        "Calendar Year": cy,
                        "Quarter": quarter,
                        "Dividend/Share": amount,
                        "Qty": qty,
                        "Gross Amount": round(payout, 2)
                    })
            
        except Exception as e:
            st.error(f"Error fetching {name}: {e}")

    my_bar.empty()

    # --- 7. ANALYSIS & TAX LOGIC ---
    if all_payouts:
        df = pd.DataFrame(all_payouts)
        
        # A. INTELLIGENT TDS CALCULATION
        tds_grouping = df.groupby(['Symbol', 'Financial Year'])['Gross Amount'].sum().reset_index()
        tds_grouping['TDS Deducted'] = tds_grouping['Gross Amount'].apply(lambda x: x * 0.10 if x > 5000 else 0)
        
        total_tds_liability = tds_grouping['TDS Deducted'].sum()
        total_gross_dividend = df['Gross Amount'].sum()
        income_tax_amount = total_gross_dividend * (tax_slab / 100)
        final_post_tax_profit = total_gross_dividend - income_tax_amount

        # --- 8. GLOBAL DASHBOARD ---
        st.subheader("📊 Lifetime Portfolio Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Dividend", f"₹{total_gross_dividend:,.2f}")
        m2.metric("TDS Deducted", f"₹{total_tds_liability:,.2f}", help="Only if >₹5k per company/FY")
        m3.metric("Tax Liability", f"₹{income_tax_amount:,.2f}", f"{tax_slab}% Slab")
        m4.metric("Post-Tax Profit", f"₹{final_post_tax_profit:,.2f}", "Real Value")

        st.markdown("---")

        # --- 9. NEW FEATURE: HISTORICAL LOOKUP ---
        st.subheader("🔎 Historical Drill-Down")
        st.markdown("Select a specific year to see your earnings for that period.")

        col_search1, col_search2 = st.columns(2)
        
        with col_search1:
            search_mode = st.radio("Group By:", ["Calendar Year (Jan-Dec)", "Financial Year (Apr-Mar)"], horizontal=True)
        
        with col_search2:
            if search_mode == "Calendar Year (Jan-Dec)":
                unique_years = sorted(df['Calendar Year'].unique(), reverse=True)
                selected_year = st.selectbox("Select Year", unique_years)
                # Filter Data
                filtered_df = df[df['Calendar Year'] == selected_year]
            else:
                unique_fys = sorted(df['Financial Year'].unique(), reverse=True)
                selected_year = st.selectbox("Select Financial Year", unique_fys)
                # Filter Data
                filtered_df = df[df['Financial Year'] == selected_year]

        if not filtered_df.empty:
            # Metrics for the Selected Year
            year_total = filtered_df['Gross Amount'].sum()
            
            # TDS for this specific year (Approximate visualization)
            # We re-run the TDS check just for the filtered view to be safe
            year_tds_df = filtered_df.groupby(['Symbol', 'Financial Year'])['Gross Amount'].sum().reset_index()
            year_tds_val = year_tds_df['Gross Amount'].apply(lambda x: x * 0.10 if x > 5000 else 0).sum()
            
            ym1, ym2, ym3 = st.columns(3)
            ym1.metric(f"Total Dividend ({selected_year})", f"₹{year_total:,.2f}")
            ym2.metric(f"TDS ({selected_year})", f"₹{year_tds_val:,.2f}")
            ym3.metric("Stock Count", len(filtered_df['Symbol'].unique()))
            
            # Quarterly Breakdown Chart
            st.caption(f"Quarterly Performance in {selected_year}")
            q_summary = filtered_df.groupby('Quarter')['Gross Amount'].sum().reset_index()
            st.bar_chart(q_summary, x="Quarter", y="Gross Amount", color="#FF4B4B")
            
            with st.expander(f"View Transaction Details for {selected_year}"):
                st.dataframe(filtered_df.sort_values(by="Ex-Date", ascending=False), use_container_width=True)
        else:
            st.warning("No data found for this selection.")

        # --- 10. DETAILED LOG ---
        st.markdown("---")
        st.subheader("📝 Full Transaction Ledger")
        st.dataframe(df.sort_values(by="Ex-Date", ascending=False), use_container_width=True)
        
    else:
        st.info("No dividends found since purchase date.")

else:
    st.info("👈 Use the smart search in the sidebar to add stocks.")

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "© 2026 | Built by **[Kevin Joseph](https://www.linkedin.com/in/kevin-joseph-in/)** | "
    "Powered by [Yahoo Finance](https://pypi.org/project/yfinance/)"
)
