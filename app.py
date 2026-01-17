import streamlit as st
import pandas as pd
import os
from datetime import date

# 1. SETUP: Define the file where we store data
DATA_FILE = "expenses.csv"

# 2. FUNCTION: Load data from the CSV file
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        # If file doesn't exist, return an empty dataframe with columns
        return pd.DataFrame(columns=["Date", "Category", "Amount", "Description"])

# 3. FUNCTION: Save data back to the CSV file
def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# 4. APP TITLE
st.title("💰 My Monthly Expense Tracker")

# 5. SIDEBAR: Input form for new expenses
st.sidebar.header("Add New Expense")
with st.sidebar.form("expense_form"):
    exp_date = st.date_input("Date", value=date.today())
    exp_category = st.selectbox("Category", ["Food", "Transport", "Utilities", "Entertainment", "Other"])
    exp_amount = st.number_input("Amount", min_value=0.0, format="%.2f")
    exp_desc = st.text_input("Description")
    
    # The submit button
    submitted = st.form_submit_button("Add Expense")

# 6. LOGIC: What happens when you click "Add Expense"
if submitted:
    # Load current data
    df = load_data()
    
    # Create a new row of data
    new_data = pd.DataFrame({
        "Date": [exp_date],
        "Category": [exp_category],
        "Amount": [exp_amount],
        "Description": [exp_desc]
    })
    
    # Combine old data with new data using pd.concat
    df = pd.concat([df, new_data], ignore_index=True)
    
    # Save it
    save_data(df)
    st.sidebar.success("Expense Added!")

# 7. MAIN AREA: Show the data
st.header("Recent Expenses")
df = load_data()

# Show the table if there is data
if not df.empty:
    # Sort by date (newest first)
    df = df.sort_values(by="Date", ascending=False)
    
    # Display the dataframe
    st.dataframe(df, use_container_width=True)

    # 8. METRICS: Show total spent
    total_spent = df["Amount"].sum()
    st.metric(label="Total Spent All Time", value=f"${total_spent:,.2f}")
else:
    st.info("No expenses tracked yet. Add one from the sidebar!")
