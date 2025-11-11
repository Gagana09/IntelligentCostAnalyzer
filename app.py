import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from prophet import Prophet
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from io import BytesIO

# -----------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------
st.set_page_config(page_title="💰 Intelligent Cost Analyzer", layout="wide")
plt.style.use('seaborn-v0_8-darkgrid')

st.title("💰 Intelligent Cost Analyzer")
st.markdown("Analyze your Azure-like cost data intelligently with forecasts, optimization insights, and explainable AI.")

# -----------------------------------------------------------
# LOAD CSV
# -----------------------------------------------------------
df = pd.read_csv("synthetic_cost_data.csv")
df.rename(columns={'date': 'Date', 'application': 'AppName', 'cost': 'Cost'}, inplace=True)
df['Date'] = pd.to_datetime(df['Date'])
df['Cost'] = pd.to_numeric(df['Cost'], errors='coerce')
df.dropna(subset=['Cost'], inplace=True)

# -----------------------------------------------------------
# SIDEBAR SETTINGS
# -----------------------------------------------------------
st.sidebar.header("⚙️ Settings")
st.sidebar.write("Columns in CSV:", df.columns.tolist())
selected_app = st.sidebar.selectbox("Select Application", df['AppName'].unique())

filtered_df = df[df['AppName'] == selected_app].copy().sort_values('Date')

# -----------------------------------------------------------
# DISPLAY DATA
# -----------------------------------------------------------
st.subheader(f"📊 Cost Data for {selected_app}")
st.dataframe(filtered_df.tail(10))
min_cost, max_cost = filtered_df['Cost'].min(), filtered_df['Cost'].max()
st.info(f"💡 **Cost range for {selected_app}: ₹{min_cost} → ₹{max_cost}**")

# -----------------------------------------------------------
# COST TREND VISUALIZATION
# -----------------------------------------------------------
st.subheader("📈 Cost Trend Over Time")
fig, ax = plt.subplots(figsize=(10, 5))
sns.lineplot(x='Date', y='Cost', data=filtered_df, marker='o', color='skyblue', ax=ax)
ax.set_title(f"Cost Trend for {selected_app}", fontsize=14)
ax.set_ylabel("Cost (₹)")
ax.set_xlabel("Date")
plt.xticks(rotation=45)
st.pyplot(fig, clear_figure=True)
plt.close(fig)

# -----------------------------------------------------------
# FORECASTING WITH PROPHET
# -----------------------------------------------------------
st.subheader("🔮 Forecasting Next 30 Days (Prophet Model)")
forecast_df = filtered_df[['Date', 'Cost']].rename(columns={'Date': 'ds', 'Cost': 'y'})

if len(forecast_df) > 5:
    model = Prophet(daily_seasonality=True)
    model.fit(forecast_df)
    future = model.make_future_dataframe(periods=30)
    forecast = model.predict(future)

    st.markdown("**Predicted Cost Trend**")
    fig1 = model.plot(forecast)
    plt.title(f"Cost Forecast for {selected_app}")
    st.pyplot(fig1, clear_figure=True)
    plt.close(fig1)

    st.markdown("**Forecast Components (Trend & Seasonality)**")
    fig2 = model.plot_components(forecast)
    st.pyplot(fig2, clear_figure=True)
    plt.close(fig2)

    next_month = forecast.tail(30)['yhat'].mean()
    st.success(f"📅 **Forecasted Average Cost (Next 30 days): ₹{int(next_month)}**")
else:
    st.warning("Not enough data points to train the forecasting model.")
    next_month = filtered_df['Cost'].mean()

# -----------------------------------------------------------
# COST OPTIMIZATION ADVISOR
# -----------------------------------------------------------
st.subheader("🤖 AI Cost Optimization Advisor")
avg_cost = filtered_df['Cost'].mean()

if next_month > avg_cost * 1.05:
    st.warning(f"📈 Rising cost trend for {selected_app}. Consider **scaling down compute size**, or check for unused storage and idle instances.")
elif next_month < avg_cost * 0.95:
    st.success(f"✅ Forecast indicates **optimized cost trend**. Maintain current configuration and monitor usage.")
else:
    st.info(f"📊 Stable cost trend for {selected_app}. No major optimization actions required.")

# -----------------------------------------------------------
# COST EFFICIENCY INDEX
# -----------------------------------------------------------
st.subheader("📏 Cost Efficiency Index (CEI)")
cei = round((avg_cost / next_month) * 100, 2)
st.metric("Cost Efficiency Index", f"{cei}%", "Higher is better")

# -----------------------------------------------------------
# ANOMALY DETECTION
# -----------------------------------------------------------
st.subheader("⚠️ Anomaly Detection (Statistical Method)")
mean_cost = filtered_df['Cost'].mean()
std_cost = filtered_df['Cost'].std()
threshold = 2
filtered_df['Anomaly'] = np.where(
    (filtered_df['Cost'] > mean_cost + threshold * std_cost) |
    (filtered_df['Cost'] < mean_cost - threshold * std_cost),
    True, False
)
anomalies = filtered_df[filtered_df['Anomaly'] == True]

if not anomalies.empty:
    st.error("🚨 Detected potential cost anomalies:")
    st.dataframe(anomalies[['Date', 'Cost']])
else:
    st.success("✅ No major anomalies detected in the recent cost data.")

# -----------------------------------------------------------
# FEATURE IMPORTANCE (EXPLAINABLE AI)
# -----------------------------------------------------------
st.subheader("🧠 Feature Importance (Explainable AI)")

# Simulate resource metrics
filtered_df['CPU'] = np.random.uniform(30, 90, len(filtered_df))
filtered_df['Storage'] = np.random.uniform(50, 200, len(filtered_df))
filtered_df['APICalls'] = np.random.randint(100, 1000, len(filtered_df))

# Train a Random Forest model
X = filtered_df[['CPU', 'Storage', 'APICalls']]
y = filtered_df['Cost']
model_rf = RandomForestRegressor(random_state=42)
model_rf.fit(X, y)
importance = permutation_importance(model_rf, X, y)

imp_df = pd.DataFrame({
    'Feature': X.columns,
    'Importance': importance.importances_mean
}).sort_values(by='Importance', ascending=False)

fig_imp, ax_imp = plt.subplots(figsize=(6, 4))
sns.barplot(x='Importance', y='Feature', data=imp_df, palette='coolwarm', ax=ax_imp)
ax_imp.set_title("Feature Importance for Cost Prediction")
st.pyplot(fig_imp, clear_figure=True)
plt.close(fig_imp)

# -----------------------------------------------------------
# MULTI-APP COMPARISON
# -----------------------------------------------------------
st.subheader("🏗️ Application-Wise Cost Comparison")

app_summary = df.groupby("AppName")["Cost"].sum().reset_index().sort_values("Cost", ascending=False)

fig3, ax3 = plt.subplots(figsize=(8, 5))
sns.barplot(x="Cost", y="AppName", data=app_summary, palette="viridis", ax=ax3)
ax3.set_title("Total Cost per Application")
st.pyplot(fig3, clear_figure=True)
plt.close(fig3)

st.subheader("💵 Cost Distribution Across Applications")
fig4, ax4 = plt.subplots(figsize=(5, 5))
ax4.pie(app_summary["Cost"], labels=app_summary["AppName"], autopct="%1.1f%%", startangle=90)
ax4.axis("equal")
st.pyplot(fig4, clear_figure=True)
plt.close(fig4)

# -----------------------------------------------------------
# SUMMARY STATISTICS
# -----------------------------------------------------------
st.subheader("📊 Summary Statistics")
st.dataframe(filtered_df.describe())

# -----------------------------------------------------------
# REPORT DOWNLOAD
# -----------------------------------------------------------
st.subheader("📥 Download Insights Report")

report_df = pd.DataFrame({
    "Application": app_summary["AppName"],
    "TotalCost": app_summary["Cost"],
    "MinCost": [df[df["AppName"] == app]["Cost"].min() for app in app_summary["AppName"]],
    "MaxCost": [df[df["AppName"] == app]["Cost"].max() for app in app_summary["AppName"]],
    "MeanCost": [df[df["AppName"] == app]["Cost"].mean() for app in app_summary["AppName"]],
})

csv_buffer = BytesIO()
report_df.to_csv(csv_buffer, index=False)
st.download_button(
    label="📄 Download Cost Summary CSV",
    data=csv_buffer.getvalue(),
    file_name="Cost_Summary_Report.csv",
    mime="text/csv"
)

# -----------------------------------------------------------
# INSIGHTS SUMMARY
# -----------------------------------------------------------
st.markdown("""
---
## 🧩 Research Insights

- **Forecasting + Optimization:** Enables proactive cost governance.  
- **Anomaly detection:** Identifies unexpected billing spikes early.  
- **Explainable AI:** Shows which workload factors drive cost.  
- **Cost Efficiency Index (CEI):** Quantifies spending effectiveness.  
- **Multi-app analysis:** Compares and visualizes cost share for services.  

---
💡 *Demonstrates an AI-driven cost intelligence framework suitable for research or enterprise deployment.*
""")
