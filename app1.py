import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from prophet import Prophet
from io import BytesIO
import smtplib
from email.message import EmailMessage
from advisor_helper import get_advisor_recommendations

# -----------------------------------------------------------
# STREAMLIT PAGE CONFIGURATION
# -----------------------------------------------------------
st.set_page_config(page_title="💰 Intelligent Cost Analyzer", layout="wide")
plt.style.use('seaborn-v0_8-darkgrid')

# -----------------------------------------------------------
# ADMIN LOGIN
# -----------------------------------------------------------
ADMIN_EMAIL = "supriya21404@gmail.com"
ADMIN_PASSWORD = "admin123"  # ⚠️ Replace with a secure one

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align:center;'>🔐 Admin Login</h1>", unsafe_allow_html=True)
    email = st.text_input("Email", placeholder="Enter admin email")
    password = st.text_input("Password", type="password", placeholder="Enter password")

    if st.button("Login"):
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            st.session_state.authenticated = True
            st.success("✅ Login successful!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials.")
    st.stop()

# -----------------------------------------------------------
# MAIN APP SECTION
# -----------------------------------------------------------
st.title("💰 Intelligent Cost Analyzer")
st.caption(f"👤 Logged in as: {ADMIN_EMAIL}")

# -----------------------------------------------------------
# CSV UPLOAD SECTION
# -----------------------------------------------------------
st.subheader("📂 Upload Azure Cost Data (CSV)")
uploaded_file = st.file_uploader("Upload cost data exported from Azure", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("✅ File uploaded successfully!")
else:
    st.info("No file uploaded — using demo data.")
    df = pd.read_csv("synthetic_cost_data.csv")

# -----------------------------------------------------------
# DATA CLEANING
# -----------------------------------------------------------
df.columns = [col.strip().lower() for col in df.columns]
rename_map = {"date": "Date", "application": "AppName", "appname": "AppName", "cost": "Cost", "pretaxcost": "Cost", "resourcergroupname": "AppName"}
df.rename(columns=rename_map, inplace=True)

if not {"Date", "AppName", "Cost"}.issubset(df.columns):
    st.error("❌ CSV must contain: Date, AppName, and Cost columns.")
    st.stop()

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df.dropna(subset=["Date"], inplace=True)

# -----------------------------------------------------------
# SIDEBAR SETTINGS
# -----------------------------------------------------------
st.sidebar.header("⚙️ Settings")
selected_app = st.sidebar.selectbox("Select Resource Group", sorted(df["AppName"].unique()))
filtered_df = df[df["AppName"] == selected_app].copy().sort_values("Date")

# -----------------------------------------------------------
# COST TREND
# -----------------------------------------------------------
st.subheader(f"📈 Cost Trend for {selected_app}")

if filtered_df.empty:
    st.warning("No data found for the selected resource group.")
else:
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(x="Date", y="Cost", data=filtered_df, marker="o", color="royalblue", ax=ax)
    ax.set_title(f"Cost Trend - {selected_app}", fontsize=13)
    ax.set_xlabel("Date")
    ax.set_ylabel("Cost (₹)")
    plt.xticks(rotation=45)
    st.pyplot(fig)
    plt.close(fig)

# -----------------------------------------------------------
# FORECASTING
# -----------------------------------------------------------
st.subheader("🔮 30-Day Cost Forecast")

if len(filtered_df) > 5:
    forecast_df = filtered_df[["Date", "Cost"]].rename(columns={"Date": "ds", "Cost": "y"})
    model = Prophet(daily_seasonality=True)
    model.fit(forecast_df)
    future = model.make_future_dataframe(periods=30)
    forecast = model.predict(future)
    next_month = forecast.tail(30)["yhat"].mean()

    fig1 = model.plot(forecast)
    plt.title(f"Forecast for {selected_app}")
    st.pyplot(fig1)
    st.success(f"📅 Predicted average cost for next 30 days: ₹{int(next_month)}")
else:
    next_month = filtered_df["Cost"].mean() if not filtered_df.empty else 0
    st.info("Not enough data for forecasting.")

# -----------------------------------------------------------
# ANOMALY DETECTION
# -----------------------------------------------------------
st.subheader("⚠️ Anomaly Detection")

if not filtered_df.empty:
    mean_cost = filtered_df["Cost"].mean()
    std_cost = filtered_df["Cost"].std()
    filtered_df["Anomaly"] = np.abs(filtered_df["Cost"] - mean_cost) > 2 * std_cost
    anomalies = filtered_df[filtered_df["Anomaly"]]

    if len(anomalies) > 0:
        st.error(f"🚨 Detected {len(anomalies)} anomalies in cost data!")
        st.dataframe(anomalies[["Date", "Cost"]])
    else:
        st.success("✅ No anomalies detected.")
else:
    st.warning("No data to check anomalies.")

# -----------------------------------------------------------
# COST EFFICIENCY INDEX
# -----------------------------------------------------------
st.subheader("📏 Cost Efficiency Index (CEI)")
avg_cost = filtered_df["Cost"].mean() if not filtered_df.empty else 0

if next_month > 0 and avg_cost > 0:
    cei = round((avg_cost / next_month) * 100, 2)
    delta = round(cei - 100, 2)
    st.metric("Cost Efficiency Index", f"{cei}%", f"{delta}% vs forecast")
else:
    st.info("Not enough data to calculate CEI.")

# -----------------------------------------------------------
# COST SUMMARY
# -----------------------------------------------------------
st.subheader("🏗️ Resource Group Cost Summary")

app_summary = df.groupby("AppName")["Cost"].agg(["sum", "min", "max", "mean"]).reset_index()
app_summary.columns = ["ResourceGroup", "TotalCost", "MinCost", "MaxCost", "MeanCost"]

total_sum = app_summary["TotalCost"].sum()
app_summary["CostShare (%)"] = (app_summary["TotalCost"] / total_sum * 100).round(2)

app_trend = df.groupby("AppName")["Cost"].apply(lambda x: "🔼 Rising" if x.iloc[-1] > x.iloc[0] else "🔽 Falling").reset_index(name="Trend")
app_trend.rename(columns={"AppName": "ResourceGroup"}, inplace=True)
app_summary = app_summary.merge(app_trend, on="ResourceGroup", how="left")

st.dataframe(app_summary)

# -----------------------------------------------------------
# COST HEATMAP
# -----------------------------------------------------------
st.subheader("🔥 Cost Efficiency Heatmap")
fig, ax = plt.subplots(figsize=(8, 4))
sns.heatmap(
    app_summary[["MeanCost", "CostShare (%)"]],
    annot=True, fmt=".1f", cmap="coolwarm", cbar=False,
    yticklabels=app_summary["ResourceGroup"]
)
ax.set_title("Cost Distribution per Resource Group")
st.pyplot(fig)

# -----------------------------------------------------------
# ADVISOR RECOMMENDATIONS
# -----------------------------------------------------------
st.subheader("💬 Azure Advisor Smart Recommendations")

if st.button("Fetch Recommendations"):
    with st.spinner("Contacting Azure Advisor..."):
        try:
            recs = get_advisor_recommendations("d6e4b3f9-95f1-4234-9b66-046747c96c0d")
            if recs:
                st.success(f"✅ Retrieved {len(recs)} recommendations.")
                rec_df = pd.DataFrame(recs)
                st.dataframe(rec_df)
            else:
                st.info("No active recommendations found.")
        except Exception as e:
            st.error(f"❌ Could not fetch Advisor data: {e}")

# -----------------------------------------------------------
# DOWNLOAD + EMAIL
# -----------------------------------------------------------
st.subheader("📥 Download / Email Report")

def send_report_email(to_email, report_bytes):
    sender_email = "acharyagagana@gmail.com"  # project mail
    sender_password = "ihnw ddcb nscg nmmf"  # App password from Gmail

    msg = EmailMessage()
    msg["Subject"] = "📊 Azure Intelligent Cost Analyzer - Report"
    msg["From"] = sender_email
    msg["To"] = to_email
    msg.set_content("Attached is your latest Azure cost analysis and recommendations report.")
    msg.add_attachment(report_bytes, maintype="application", subtype="octet-stream", filename="Azure_Cost_Analysis.xlsx")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender_email, sender_password)
        smtp.send_message(msg)

if st.button("📧 Email Full Report to Admin"):
    with st.spinner("Generating and sending report..."):
        try:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                app_summary.to_excel(writer, sheet_name="Cost Summary", index=False)
                if "rec_df" in locals():
                    rec_df.to_excel(writer, sheet_name="Advisor Tips", index=False)
                filtered_df.to_excel(writer, sheet_name="Selected RG Details", index=False)
            send_report_email(ADMIN_EMAIL, output.getvalue())
            st.success("✅ Report emailed successfully to admin!")
        except Exception as e:
            st.error(f"❌ Failed to send email: {e}")

# -----------------------------------------------------------
# PROJECT SUMMARY
# -----------------------------------------------------------
st.markdown("""
---
## 🧩 Project Summary

This intelligent cost analyzer helps Azure admins:
- Track and visualize **resource group-level cost trends**
- Forecast spending using **Prophet AI**
- Detect **anomalies** and evaluate **cost efficiency**
- Retrieve **Azure Advisor recommendations** for optimization
- Generate and email **automated reports**

This makes cloud cost governance proactive, data-driven, and intelligent 🚀
""")
