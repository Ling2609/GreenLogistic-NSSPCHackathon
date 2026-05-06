# use --streamlit run app.py-- to run the app

import streamlit as st
import pandas as pd
import os

# --- PAGE SETUP ---
st.set_page_config(page_title="Green Logistics Dashboard", page_icon="🥬", layout="wide")
st.title("🥬 Cooperative Supply Chain Dashboard")
st.markdown("### Proposal A (Direct Shipping) vs. Proposal B (Regional Milk Runs)")

# --- LOAD EXCEL DATA ---
# This looks for the files in the same folder as the app.py script
script_dir = os.path.dirname(os.path.abspath(__file__))
file_a = os.path.join(script_dir, 'Step5_Master_Scenario_Results_Patched.xlsx')
file_b = os.path.join(script_dir, 'Step6_Proposal_B_MilkRun_Results.xlsx')

@st.cache_data
def load_data():
    # Load the KPI tabs
    df_a = pd.read_excel(file_a, sheet_name='KPI_Comparison', index_col=0)
    df_b = pd.read_excel(file_b, sheet_name='KPI_Comparison', index_col=0)
    return df_a, df_b

try:
    prop_a, prop_b = load_data()
except FileNotFoundError:
    st.error("⚠️ Excel files not found. Please ensure Step 5 and Step 6 Excel files are in the same folder as this script.")
    st.stop()

# --- SIDEBAR: INTERACTIVE CONTROLS ---
st.sidebar.header("Simulation Controls")
selected_scenario = st.sidebar.selectbox(
    "Select a Disaster/Demand Scenario:",
    options=['S0', 'S1', 'S2a', 'S2b', 'S2c'],
    format_func=lambda x: f"{x}: {prop_a.loc['Name', x]}"
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Scenario Legend:**\n* **S0**: Normal Baseline\n* **S1**: +30% Peak Demand\n* **S2a**: 20% Crop Loss (Cameron Highlands)\n* **S2b**: 20% Crop Loss (Batang Berjuntai)\n* **S2c**: 20% Crop Loss (Air Hitam)")

# --- MAIN DASHBOARD: METRICS ---
st.subheader(f"📊 Results for {selected_scenario}: {prop_a.loc['Name', selected_scenario]}")

# Extract numbers for the selected scenario
cost_a = prop_a.loc['Total Cost (RM)', selected_scenario]
cost_b = prop_b.loc['Total Cost (RM)', selected_scenario]
savings_rm = cost_a - cost_b
savings_pct = (savings_rm / cost_a) * 100

fuel_a = prop_a.loc['Total Fuel (L)', selected_scenario]
fuel_b = prop_b.loc['Total Fuel (L)', selected_scenario]

trucks_a = prop_a.loc['Total Trucks', selected_scenario]
trucks_b = prop_b.loc['Total Trucks', selected_scenario]

# Display massive "Hero" metrics
col1, col2, col3 = st.columns(3)
col1.metric("Total Cost (Proposal B)", f"RM {cost_b:,.2f}", f"-RM {savings_rm:,.2f} Savings", delta_color="inverse")
col2.metric("Total Fuel Consumed", f"{fuel_b:,.1f} L", f"-{(fuel_a - fuel_b):,.1f} L Saved", delta_color="inverse")
col3.metric("Fleet Trucks Deployed", f"{trucks_b}", f"-{(trucks_a - trucks_b)} Trucks Off Road", delta_color="inverse")

st.markdown("---")

# --- CHARTS & COMPARISONS ---
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### 💰 Cost Comparison")
    # Prepare data for bar chart
    chart_data = pd.DataFrame({
        "Proposal A (Direct)": [cost_a],
        "Proposal B (Milk Run)": [cost_b]
    }, index=["Total Cost (RM)"])
    st.bar_chart(chart_data.T)

with col_right:
    st.markdown("#### 🚚 Environmental Impact (Fuel L)")
    fuel_data = pd.DataFrame({
        "Proposal A (Direct)": [fuel_a],
        "Proposal B (Milk Run)": [fuel_b]
    }, index=["Fuel Consumed (Liters)"])
    st.bar_chart(fuel_data.T, color="#A9D08E")

# --- RAW DATA EXPANDER ---
with st.expander("🔍 View Raw KPI Data Tables"):
    st.markdown("**Proposal A (Direct Shipping)**")
    st.dataframe(prop_a, use_container_width=True)
    st.markdown("**Proposal B (Milk Run Consolidation)**")
    st.dataframe(prop_b, use_container_width=True)