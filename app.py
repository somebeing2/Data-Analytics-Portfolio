import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import date
from io import BytesIO

# 1. SETUP: Define the file where we store data
DATA_FILE = "expenses.csv"

# 2. FUNCTION: Load data from the CSV file
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=["Date", "Category", "Amount", "Description"])

# 3. FUNCTION: Save data back to the CSV file
def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# 4. FUNCTION: Convert DataFrame to Excel for download
def to_excel(df):
    output = BytesIO()
    # Use 'openpyxl' engine for writing Excel files
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Expenses')
    return output.getvalue()

# 5. APP TITLE
st.title("💰 My Monthly Expense Tracker")

# 6. SIDEBAR: Input form for new expenses
st.sidebar.header("Add New Expense")
with st.sidebar.form("expense_form"):
    exp_date = st.date_input("Date", value=date.today())
    exp_category = st.selectbox("Category", ["Food", "Transport", "Utilities", "Entertainment", "Other"])
    # Changed format to handle generic float, display logic handles the symbol
    exp_amount = st.number_input("Amount (₹)", min_value=0.0, format="%.2f")
    exp_desc = st.text_input("Description")
    
    submitted = st.form_submit_button("Add Expense")

# 7. LOGIC: What happens when you click "Add Expense"
if submitted:
    df = load_data()
    new_data = pd.DataFrame({
        "Date": [exp_date],
        "Category": [exp_category],
        "Amount": [exp_amount],
        "Description": [exp_desc]
    })
    df = pd.concat([df, new_data], ignore_index=True)
    save_data(df)
    st.sidebar.success("Expense Added!")

# 8. MAIN AREA: Show the data and charts
st.header("Your Expenses")
df = load_data()

if not df.empty:
    # Ensure the Date column is actually treated as dates for sorting
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    df = df.sort_values(by="Date", ascending=False)
    
    # --- FEATURE 1: Rupee Sign & Metrics ---
    total_spent = df["Amount"].sum()
    # We use the currency symbol directly in the string format
    st.metric(label="Total Spent All Time", value=f"₹{total_spent:,.2f}")

    # --- FEATURE 2: Pie Chart ---
    st.subheader("Expenses by Category")
    # We group data by Category to sum the amounts
    category_totals = df.groupby("Category")["Amount"].sum().reset_index()
    
    # Create the chart using Plotly
    fig = px.pie(category_totals, values="Amount", names="Category", 
                 title="Where is the money going?", hole=0.3)
    st.plotly_chart(fig)

    # Display the dataframe
    st.dataframe(df, use_container_width=True)

    # --- FEATURE 3: Excel Download ---
    excel_data = to_excel(df)
    st.download_button(
        label="📥 Download Data as Excel",
        data=excel_data,
        file_name='my_expenses.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

else:
    st.info("No expenses tracked yet. Add one from the sidebar!")
