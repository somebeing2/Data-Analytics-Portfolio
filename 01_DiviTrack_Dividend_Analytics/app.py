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
                    
                    all_payouts.append({
                        "Stock": name,
                        "Symbol": ticker,
                        "Ex-Date": date_val.date(),
                        "Financial Year": fy,
                        "Calendar Year": cy,
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
        # TDS applies if Total Dividend from ONE Company in ONE Financial Year > ₹5,000
        
        # Group by Stock and Financial Year
        tds_grouping = df.groupby(['Symbol', 'Financial Year'])['Gross Amount'].sum().reset_index()
        tds_grouping['TDS Deducted'] = tds_grouping['Gross Amount'].apply(lambda x: x * 0.10 if x > 5000 else 0)
        
        # Merge TDS back to main data for visibility (Optional, but good for auditing)
        # For the dashboard, we just need the total TDS sum
        total_tds_liability = tds_grouping['TDS Deducted'].sum()
        total_gross_dividend = df['Gross Amount'].sum()
        
        # Tax Liability (Slab)
        income_tax_amount = total_gross_dividend * (tax_slab / 100)
        
        # Final Net
        # Note: You pay tax on the GROSS amount. TDS is just a pre-payment.
        # Net In-Hand = Gross - TDS (Immediate) 
        # But 'Real' Profit after Tax Filing = Gross - Tax Liability
        
        final_post_tax_profit = total_gross_dividend - income_tax_amount

        # --- 8. DASHBOARD METRICS ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Dividend", f"₹{total_gross_dividend:,.2f}")
        m2.metric("TDS Deducted", f"₹{total_tds_liability:,.2f}", help="Only if >₹5k per company/FY")
        m3.metric("Tax Liability", f"₹{income_tax_amount:,.2f}", f"{tax_slab}% Slab")
        m4.metric("Post-Tax Profit", f"₹{final_post_tax_profit:,.2f}", "Real Value")

        # --- 9. YEARLY BREAKDOWNS ---
        st.subheader("📅 Yearly Breakdown")
        
        tab1, tab2 = st.tabs(["🏛️ Financial Year View", "🗓️ Calendar Year View"])
        
        with tab1:
            # Group by FY
            fy_summary = df.groupby('Financial Year')['Gross Amount'].sum().reset_index()
            fy_summary = fy_summary.sort_values('Financial Year', ascending=False)
            st.dataframe(fy_summary, use_container_width=True, hide_index=True)
            
            # Chart
            st.bar_chart(fy_summary, x="Financial Year", y="Gross Amount", color="#29B5E8")

        with tab2:
            # Group by Calendar Year
            cy_summary = df.groupby('Calendar Year')['Gross Amount'].sum().reset_index()
            cy_summary = cy_summary.sort_values('Calendar Year', ascending=False)
            # Convert Year to String to avoid comma formatting (e.g. 2,024)
            cy_summary['Calendar Year'] = cy_summary['Calendar Year'].astype(str)
            st.dataframe(cy_summary, use_container_width=True, hide_index=True)
            
            # Chart
            st.bar_chart(cy_summary, x="Calendar Year", y="Gross Amount", color="#00C853")

        # --- 10. DETAILED LOG ---
        st.subheader("📝 Transaction Ledger")
        st.dataframe(df.sort_values(by="Ex-Date", ascending=False), use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Ledger (CSV)",
            data=csv,
            file_name='dividend_statement.csv',
            mime='text/csv',
        )
    else:
        st.info("No dividends found since purchase date.")

else:
    st.info("👈 Use the smart search in the sidebar to add stocks.")

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "© 2026 | Built by **[Kevin Joseph](https://www.linkedin.com/in/kevin-joseph-in/)** | "
    "Powered by [Yahoo Finance](https://pypi.org/project/yfinance/)")
