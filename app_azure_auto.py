import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from prophet import Prophet
from io import BytesIO
import smtplib
from email.message import EmailMessage
from azure.identity import DeviceCodeCredential
from azure.mgmt.costmanagement import CostManagementClient
from advisor_helper import get_advisor_recommendations

# -----------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------
st.set_page_config(page_title="💰 Azure Intelligent Cost Analyzer", layout="wide")
plt.style.use('seaborn-v0_8-darkgrid')

# Admin credentials
ADMIN_EMAIL = "supriya21404@gmail.com"  # ✅ Fixed typo
SENDER_EMAIL = "acharyagagana@gmail.com"
SENDER_PASSWORD = "ihnwddcbnscgnmmf"  # ✅ Gmail App Password (no spaces)
SUBSCRIPTION_ID = "d6e4b3f9-95f1-4234-9b66-046747c96c0d"

# -----------------------------------------------------------
# FETCH COST DATA DIRECTLY FROM AZURE
# -----------------------------------------------------------
@st.cache_data
def fetch_cost_data():
    st.info("🔐 Authenticating with Azure... please approve device code in browser.")
    credential = DeviceCodeCredential()
    cost_client = CostManagementClient(credential)
    scope = f"/subscriptions/{SUBSCRIPTION_ID}"

    query = {
        "type": "Usage",
        "timeframe": "MonthToDate",
        "dataset": {
            "granularity": "Daily",
            "aggregation": {"totalCost": {"name": "PreTaxCost", "function": "Sum"}},
            "grouping": [{"type": "Dimension", "name": "ResourceGroupName"}]
        }
    }
    response = cost_client.query.usage(scope=scope, parameters=query)

    rows = []
    for r in response.rows:
        rows.append({
            "Date": str(int(r[1])),
            "AppName": r[2],
            "Cost": r[0],
            "Currency": r[3]
        })
    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d")
    return df

# -----------------------------------------------------------
# APP HEADER
# -----------------------------------------------------------
st.title("💰 Azure Intelligent Cost Analyzer (Admin Mode)")

df = fetch_cost_data()
st.success("✅ Live Azure cost data retrieved successfully!")

# -----------------------------------------------------------
# ANALYSIS SECTION
# -----------------------------------------------------------
selected_app = st.sidebar.selectbox("Select Resource Group", sorted(df["AppName"].unique()))
filtered_df = df[df["AppName"] == selected_app].copy().sort_values("Date")

# Cost Trend
st.subheader(f"📈 Cost Trend for {selected_app}")
fig, ax = plt.subplots(figsize=(10, 5))
sns.lineplot(x="Date", y="Cost", data=filtered_df, marker="o", color="royalblue", ax=ax)
ax.set_xlabel("Date")
ax.set_ylabel("Cost (₹)")
st.pyplot(fig)
plt.close(fig)

# -----------------------------------------------------------
# FORECASTING
# -----------------------------------------------------------
if len(filtered_df) > 5:
    forecast_df = filtered_df[["Date", "Cost"]].rename(columns={"Date": "ds", "Cost": "y"})
    model = Prophet(daily_seasonality=True)
    model.fit(forecast_df)
    future = model.make_future_dataframe(periods=30)
    forecast = model.predict(future)
    next_month = forecast.tail(30)["yhat"].mean()
    st.success(f"📅 Forecasted average next-30-day cost: ₹{int(next_month)}")
else:
    next_month = filtered_df["Cost"].mean()

# -----------------------------------------------------------
# ANOMALY DETECTION
# -----------------------------------------------------------
st.subheader("⚠️ Anomaly Detection")
mean_cost, std_cost = filtered_df["Cost"].mean(), filtered_df["Cost"].std()
filtered_df["Anomaly"] = np.abs(filtered_df["Cost"] - mean_cost) > 2 * std_cost
if filtered_df["Anomaly"].any():
    st.error("🚨 Anomalies detected!")
    st.dataframe(filtered_df[filtered_df["Anomaly"]][["Date", "Cost"]])
else:
    st.success("✅ No anomalies detected.")

# -----------------------------------------------------------
# COST EFFICIENCY INDEX (CEI)
# -----------------------------------------------------------
avg_cost = filtered_df["Cost"].mean()
if next_month > 0 and avg_cost > 0:
    cei = round((avg_cost / next_month) * 100, 2)
    st.metric("📊 Cost Efficiency Index (Higher is better)", f"{cei}%")
else:
    st.info("Not enough data to calculate CEI.")

# -----------------------------------------------------------
# RESOURCE GROUP COST SUMMARY
# -----------------------------------------------------------
st.subheader("🏗️ Resource Group Cost Summary")
app_summary = df.groupby("AppName")["Cost"].agg(["sum", "min", "max", "mean"]).reset_index()
app_summary.columns = ["ResourceGroup", "TotalCost", "MinCost", "MaxCost", "MeanCost"]
total_sum = app_summary["TotalCost"].sum()
app_summary["CostShare (%)"] = (app_summary["TotalCost"] / total_sum * 100).round(2)
st.dataframe(app_summary)

# -----------------------------------------------------------
# COST EFFICIENCY HEATMAP
# -----------------------------------------------------------
st.subheader("🔥 Cost Efficiency Heatmap")

heatmap_df = app_summary.sort_values("TotalCost", ascending=False).reset_index(drop=True)
top_n = 15
if len(heatmap_df) > top_n:
    st.caption(f"Showing top {top_n} resource groups by total cost.")
    heatmap_df = heatmap_df.head(top_n)

fig_height = max(1, len(heatmap_df) * 0.5)
fig, ax = plt.subplots(figsize=(10, fig_height))
sns.heatmap(
    heatmap_df[["MeanCost", "CostShare (%)"]],
    annot=True, fmt=".1f", cmap="coolwarm", cbar=True,
    yticklabels=heatmap_df["ResourceGroup"], linewidths=0.4, linecolor="black"
)
ax.set_title("Cost Distribution per Resource Group", fontsize=13, pad=15)
ax.set_xlabel("Metrics")
ax.set_ylabel("Resource Group")
plt.xticks(rotation=0)
plt.yticks(fontsize=9)
st.pyplot(fig)
plt.close(fig)

# -----------------------------------------------------------
# AZURE ADVISOR RECOMMENDATIONS
# -----------------------------------------------------------
st.subheader("💡 Azure Advisor Recommendations")

try:
    recs = get_advisor_recommendations(SUBSCRIPTION_ID)
    if recs and len(recs) > 0:
        rec_df = pd.DataFrame(recs)
        st.success(f"✅ Retrieved {len(rec_df)} live recommendations from Azure Advisor")
        st.dataframe(rec_df)
    else:
        st.warning("ℹ️ No active Azure Advisor recommendations found.")
        st.caption("🔍 Showing simulated optimization insights (for demo).")
        rec_df = pd.DataFrame([
            {"Category": "Cost", "Impact": "High", "Recommendation": "Resize or shut down idle VMs to save ₹3,500/month"},
            {"Category": "Performance", "Impact": "Medium", "Recommendation": "Use SSD-based storage for faster response times"},
            {"Category": "Security", "Impact": "High", "Recommendation": "Enable Defender for Cloud and JIT VM access"},
            {"Category": "Operational Excellence", "Impact": "Low", "Recommendation": "Add resource tags for tracking"}
        ])
        st.dataframe(rec_df)
except Exception as e:
    st.error(f"❌ Azure Advisor API error: {e}")

# -----------------------------------------------------------
# EMAIL REPORT (HTML Summary + Excel)
# -----------------------------------------------------------
st.subheader("📧 Email Automated Report")

def send_report_email(to_email, report_bytes, summary_html):
    msg = EmailMessage()
    msg["Subject"] = "📊 Azure Cost Intelligence Report"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg.set_content("Attached is your latest Azure cost and optimization report.")
    msg.add_alternative(summary_html, subtype="html")
    msg.add_attachment(report_bytes, maintype="application", subtype="octet-stream", filename="Azure_Cost_Report.xlsx")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
        smtp.send_message(msg)

if st.button("📨 Email Admin Report"):
    with st.spinner("Generating and emailing report..."):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            app_summary.to_excel(writer, sheet_name="Cost Summary", index=False)
            filtered_df.to_excel(writer, sheet_name="Selected RG", index=False)
            if "rec_df" in locals():
                rec_df.to_excel(writer, sheet_name="Advisor Recs", index=False)

        # HTML summary for email body
        summary_html = f"""
        <html>
        <body>
        <h2>📊 Azure Cost Intelligence Summary</h2>
        <p>Hello Admin,</p>
        <p>Here’s your latest Azure cost report overview:</p>
        <ul>
            <li><b>Total Resource Groups:</b> {len(df["AppName"].unique())}</li>
            <li><b>Date Range:</b> {df["Date"].min().date()} → {df["Date"].max().date()}</li>
            <li><b>Top Costly Resource Group:</b> {app_summary.iloc[0]['ResourceGroup']}</li>
            <li><b>Predicted Avg Next Month Cost:</b> ₹{int(next_month)}</li>
        </ul>
        <p>Full report attached with detailed trends, anomalies, and Advisor recommendations.</p>
        <p>Best,<br><b>Azure Intelligent Cost Analyzer</b></p>
        </body></html>
        """

        send_report_email(ADMIN_EMAIL, buffer.getvalue(), summary_html)
        st.success(f"✅ Report emailed to {ADMIN_EMAIL}")

# -----------------------------------------------------------
# FOOTER
# -----------------------------------------------------------
st.markdown("""
---
### 🌐 Intelligent Azure Cost Analyzer (Admin Mode)
Automatically fetches live cost data, forecasts spending, detects anomalies, and emails a complete optimization report to the admin.
""")
