FreedomCalc: Financial Independence Simulator
FreedomCalc is a financial projection tool designed to assist users in planning for Financial Independence, Retire Early (FIRE). Unlike standard compound interest calculators that assume a constant rate of return, this engine employs Monte Carlo simulations to model market volatility and sequence of returns risk.

It calculates the "Real Portfolio Value," adjusting all figures for inflation to show results in today's purchasing power.

Live Demo[https://data-analytics-portfolio-yv53b7xjbyjdxipu4qxwbo.streamlit.app/]

Features
Real-Value Projection: All monetary values are adjusted for inflation, allowing users to plan based on today's cost of living.

Monte Carlo Simulation: Runs 10 to 200 random market simulations based on user-defined volatility settings to visualize potential risks and worst-case scenarios.

Deterministic Baseline: Plots a standard "Average Scenario" line for comparison against volatile market paths.

FIRE Metrics: Automatically calculates the retirement corpus, applies the "4% Rule" to determine safe withdrawal rates, and assesses if the user is on track.

Data Export: Allows users to download the raw simulation data as a CSV file for further analysis in Excel or other tools.
Usage Guide
Sidebar Inputs: Enter your current age, target retirement age, current portfolio size, monthly investment (SIP), and estimated monthly expenses.

Market Assumptions: Adjust the expected annual return, inflation rate, and market volatility.

Volatility Tip: Higher volatility increases the spread between the best and worst-case simulation lines.

Run Simulation: Click the button to generate projections.

Analysis:

Grey Lines: Represent random market simulations (possible futures).

Red Line: Represents the mathematical average path.

Metrics: Review the bottom section to see if your projected corpus meets the "25x Rule" required for financial independence.

Technologies Used
Python: Core programming language.

Streamlit: Frontend framework for the web interface.

NumPy: Used for generating random normal distributions (Gaussian) for Monte Carlo logic.

Pandas: Used for data handling and structuring the simulation output.

Disclaimer
This tool is for educational and informational purposes only. It does not constitute financial advice. Market assumptions are based on historical approximations and do not guarantee future performance.
