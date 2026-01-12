import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="FreedomCalc | FIRE Simulator", layout="wide")

st.title("🔥 FreedomCalc: Financial Independence Simulator")
st.markdown("""
This engine projects your **Real Portfolio Value** (adjusted for purchasing power) over time.
It uses **Monte Carlo simulations** to test how your portfolio survives different market conditions.
""")

# --- 2. SIDEBAR INPUTS ---
st.sidebar.header("📝 Created by Kevin Joseph") 

current_age = st.sidebar.number_input("Current Age", 20, 60, 25)
retirement_age = st.sidebar.number_input("Target Retirement Age", 30, 80, 45)
current_savings = st.sidebar.number_input("Current Portfolio (₹)", 0, 100000000, 500000, step=100000)
monthly_contribution = st.sidebar.number_input("Monthly SIP (₹)", 0, 1000000, 25000, step=1000)
monthly_expense = st.sidebar.number_input("Est. Monthly Expense (Today's Value)", 0, 500000, 40000, step=1000)

st.sidebar.header("⚙️ Market Assumptions")
expected_return = st.sidebar.slider("Expected Annual Return (%)", 5.0, 20.0, 12.0) / 100
inflation_rate = st.sidebar.slider("Inflation Rate (%)", 3.0, 10.0, 6.0) / 100
volatility = st.sidebar.slider("Market Volatility (%)", 5.0, 30.0, 15.0, help="Standard deviation of returns (Risk)") / 100

simulations = st.sidebar.slider("Number of Simulations", 10, 200, 50)

# --- 3. SIMULATION LOGIC ---
years_to_invest = retirement_age - current_age
months_to_invest = years_to_invest * 12
years_after_retirement = 40 # Standard planning horizon
total_months = (years_to_invest + years_after_retirement) * 12

if st.sidebar.button("🚀 Run Simulation"):
    
    # A. Deterministic Projection (The "Average" Case)
    # We calculate 'Real' return (approx) = Return - Inflation
    real_return_monthly = (1 + expected_return) ** (1/12) - 1
    inflation_monthly = (1 + inflation_rate) ** (1/12) - 1
    real_rate = (1 + expected_return) / (1 + inflation_rate) - 1
    real_rate_monthly = (1 + real_rate) ** (1/12) - 1

    future_portfolio = []
    corpus = current_savings
    
    # Growth Phase
    for m in range(months_to_invest):
        corpus = corpus * (1 + real_rate_monthly) + monthly_contribution
        future_portfolio.append(corpus)
    
    start_retirement_corpus = corpus
    
    # Withdrawal Phase
    for m in range(years_after_retirement * 12):
        corpus = corpus * (1 + real_rate_monthly) - monthly_expense
        if corpus < 0: corpus = 0
        future_portfolio.append(corpus)

    # B. Monte Carlo Simulation (The "Random" Cases)
    sim_data = []
    
    for sim in range(simulations):
        sim_corpus = current_savings
        sim_path = []
        
        # We simulate monthly returns with volatility
        # Monthly Volatility approx = Annual Volatility / sqrt(12)
        monthly_vol = volatility / np.sqrt(12)
        
        for m in range(total_months):
            # Random monthly return
            random_return = np.random.normal(real_rate_monthly, monthly_vol)
            
            # Logic: Grow by random return, Add SIP (if working) or Subtract Expense (if retired)
            if m < months_to_invest:
                sim_corpus = sim_corpus * (1 + random_return) + monthly_contribution
            else:
                sim_corpus = sim_corpus * (1 + random_return) - monthly_expense
            
            if sim_corpus < 0: sim_corpus = 0
            sim_path.append(sim_corpus)
        
        sim_data.append(sim_path)

    # --- 4. PLOTTING ---
    st.divider()
    
    # Create DataFrame for Chart
    chart_data = pd.DataFrame(sim_data).T
    chart_data['Average Scenario'] = future_portfolio # Add the straight line
    
    # X-Axis Labels (Age)
    x_axis = np.linspace(current_age, current_age + (total_months/12), total_months)
    chart_data.index = x_axis
    
    st.subheader(f"📊 Portfolio Value Simulation (Real Purchasing Power)")
    
    # Interactive Line Chart
    st.line_chart(chart_data, color=["#d3d3d3"] * simulations + ["#FF4B4B"]) 
    # Note: The last line (Red) represents the deterministic 'Average' path.

    # --- 5. METRICS ---
    col1, col2, col3 = st.columns(3)
    
    projected_corpus = start_retirement_corpus
    safe_withdrawal_amount = projected_corpus * 0.04 / 12 # 4% Rule
    
    col1.metric("Corpus at Age " + str(retirement_age), f"₹{projected_corpus/10000000:.2f} Cr", "Real Value")
    col2.metric("Safe Monthly Income (4% Rule)", f"₹{safe_withdrawal_amount:,.0f}", f"Target: ₹{monthly_expense:,}")
    
    success_rate = 100
    if projected_corpus < (monthly_expense * 12 * 25): # 25x Rule Check
        col3.metric("FIRE Status", "❌ Gap Found", f"Need ₹{(monthly_expense*300 - projected_corpus)/10000000:.1f} Cr more")
        success_rate = 0
    else:
        col3.metric("FIRE Status", "✅ Ready!", "You are financially free")

    # --- 6. EXPORT ---
    st.markdown("---")
    csv = chart_data.to_csv().encode('utf-8')
    st.download_button("📥 Download Simulation Data", csv, "fire_simulation.csv", "text/csv")

else:
    st.info("👈 Adjust parameters and click **Run Simulation**")

# --- 7. FOOTER ---
st.markdown("---")
st.markdown(
    "© 2026 | Built by **[Kevin Joseph](https://www.linkedin.com/in/kevin-joseph-in/)** | "
    "Powered by [Streamlit](https://streamlit.io) & [NumPy](https://numpy.org/)"
)
st.caption("Disclaimer: This tool is for educational purposes and does not constitute financial advice.")
