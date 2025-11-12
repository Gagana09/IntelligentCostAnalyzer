import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from prophet import Prophet
from io import BytesIO
import smtplib
from email.message import EmailMessage
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from auth_helpers import load_users, save_users, hash_password, check_password, create_user, find_user_by_email

# -----------------------------------------------------------
# STREAMLIT PAGE CONFIGURATION
# -----------------------------------------------------------
st.set_page_config(page_title="💰 Intelligent Cost Analyzer", layout="wide")
plt.style.use('seaborn-v0_8-darkgrid')

# -----------------------------------------------------------
# LOGIN / REGISTER SCREEN (Centered)
# -----------------------------------------------------------
st.markdown("""
    <style>
    .main {display: flex; justify-content: center; align-items: center; height: 90vh;}
    .block-container {max-width: 600px; margin: auto; padding: 2rem; background-color: #1E1E1E;
                      border-radius: 15px; box-shadow: 0px 0px 25px rgba(0,0,0,0.5);}
    </style>
""", unsafe_allow_html=True)

if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.markdown("<h1 style='text-align:center;'>💰 Intelligent Cost Analyzer</h1>", unsafe_allow_html=True)
    mode = st.radio("Choose Mode", ["🔐 Login", "📝 Register"], horizontal=True)

    if mode == "📝 Register":
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Register"):
            try:
                create_user(name, email, password)
                st.success("✅ Account created! Please login now.")
            except Exception as e:
                st.error(f"❌ {e}")
    else:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = find_user_by_email(email)
            if user and check_password(password, user["password"]):
                st.session_state.user = user
                st.success(f"Welcome back, {user['name']} 👋")
                st.rerun()
            else:
                st.error("Invalid email or password.")
    st.stop()

# -----------------------------------------------------------
# MAIN APP SECTION
# -----------------------------------------------------------
user_email = st.session_state.user["email"]
st.title("💰 Intelligent Cost Analyzer")
st.caption(f"👤 Logged in as: {user_email}")

# -----------------------------------------------------------
# CSV UPLOAD SECTION
# -----------------------------------------------------------
st.subheader("📂 Upload Your Cost CSV File")
uploaded_file = st.file_uploader("Upload your cost data (CSV)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("✅ File uploaded successfully!")
else:
    st.info("No file uploaded — using demo data for now.")
    df = pd.read_csv("synthetic_cost_data.csv")

# -----------------------------------------------------------
# COLUMN NORMALIZATION
# -----------------------------------------------------------
df.columns = [col.strip().lower() for col in df.columns]
rename_map = {"date": "Date", "application": "AppName", "appname": "AppName", "cost": "Cost"}
df.rename(columns=rename_map, inplace=True)

if not {"Date", "AppName", "Cost"}.issubset(df.columns):
    st.error("❌ CSV must have columns: Date, AppName, and Cost")
    st.stop()

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df.dropna(subset=["Date"], inplace=True)

# -----------------------------------------------------------
# SIDEBAR SETTINGS
# -----------------------------------------------------------
st.sidebar.header("⚙️ Settings")
selected_app = st.sidebar.selectbox("Select Application", sorted(df["AppName"].unique()))
filtered_df = df[df["AppName"] == selected_app].copy().sort_values("Date")

# -----------------------------------------------------------
# COST TREND VISUALIZATION
# -----------------------------------------------------------
st.subheader(f"📈 Cost Trend for {selected_app}")

if filtered_df.empty:
    st.warning("No data found for the selected application.")
else:
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(x="Date", y="Cost", data=filtered_df, marker="o", color="deepskyblue", ax=ax)
    ax.set_title(f"Cost Trend - {selected_app}", fontsize=13)
    ax.set_xlabel("Date")
    ax.set_ylabel("Cost (₹)")
    plt.xticks(rotation=45)
    st.pyplot(fig)
    plt.close(fig)

# -----------------------------------------------------------
# FORECASTING
# -----------------------------------------------------------
st.subheader("🔮 Forecasting Next 30 Days")

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
    plt.close(fig1)

    st.success(f"📅 Predicted average cost for next 30 days: ₹{int(next_month)}")
else:
    st.info("Not enough data for forecasting.")
    next_month = filtered_df["Cost"].mean() if not filtered_df.empty else 0

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
        st.error("🚨 Detected anomalies in cost data!")
        st.dataframe(anomalies[["Date", "Cost"]])
    else:
        st.success("✅ No anomalies detected.")
else:
    st.warning("No data to check anomalies.")

# -----------------------------------------------------------
# COST EFFICIENCY INDEX (CEI)
# -----------------------------------------------------------
st.subheader("📏 Cost Efficiency Index (CEI)")

if not filtered_df.empty:
    avg_cost = filtered_df["Cost"].mean()
    if next_month > 0 and avg_cost > 0:
        cei = round((avg_cost / next_month) * 100, 2)
        delta = round(cei - 100, 2)
        st.metric("Cost Efficiency Index (Higher is better)", f"{cei}%", f"{delta}% vs Forecast")
    else:
        st.info("Not enough data to calculate CEI.")

# -----------------------------------------------------------
# APPLICATION-WISE SUMMARY
# -----------------------------------------------------------
st.subheader("🏗️ Application-Wise Cost Summary")
app_summary = df.groupby("AppName")["Cost"].agg(["sum", "min", "max", "mean"]).reset_index()
app_summary.columns = ["Application", "TotalCost", "MinCost", "MaxCost", "MeanCost"]
total_sum = app_summary["TotalCost"].sum()
app_summary["CostShare (%)"] = (app_summary["TotalCost"] / total_sum * 100).round(2)

# Add trend and insights
app_trend = df.groupby("AppName")["Cost"].apply(lambda x: "🔼 Rising" if x.iloc[-1] > x.iloc[0] else "🔽 Falling").reset_index(name="Trend")
app_trend.rename(columns={"AppName": "Application"}, inplace=True)
app_summary = app_summary.merge(app_trend, on="Application", how="left")
app_summary["Insight"] = app_summary["MeanCost"].apply(lambda x: "⚠️ Optimize resources" if x > 8000 else "✅ Stable cost efficiency" if x > 4000 else "💡 Scale resources smartly")

st.dataframe(app_summary)

# -----------------------------------------------------------
# PDF REPORT GENERATOR
# -----------------------------------------------------------
st.subheader("📥 Download / Email Report")

def generate_pdf_report(df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("💰 Intelligent Cost Analyzer – Summary Report", styles['Title']))
    elements.append(Spacer(1, 12))

    data = [df.columns.to_list()] + df.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E86C1")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#E8F8F5")),
        ("GRID", (0, 0), (-1, -1), 1, colors.gray),
    ]))
    elements.append(table)

    elements.append(Spacer(1, 18))
    elements.append(Paragraph("📊 Key Insights:", styles['Heading2']))
    elements.append(Paragraph("- Forecasting and anomaly detection applied per application.", styles['Normal']))
    elements.append(Paragraph("- CEI quantifies efficiency of current vs predicted costs.", styles['Normal']))
    elements.append(Paragraph("- Apps with higher mean costs are flagged for optimization.", styles['Normal']))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

pdf_report = generate_pdf_report(app_summary)
st.download_button("📄 Download PDF Report", pdf_report, "Cost_Analysis_Report.pdf", "application/pdf")

# -----------------------------------------------------------
# EMAIL FEATURE
# -----------------------------------------------------------
def send_report_email(to_email, report_bytes):
    sender_email = "acharyagagana@gmail.com"  # your project email
    sender_password = "ihnw ddcb nscg nmmf"   # Gmail app password
    msg = EmailMessage()
    msg["Subject"] = "📊 Intelligent Cost Analyzer – Detailed Report"
    msg["From"] = sender_email
    msg["To"] = to_email
    msg.set_content("Hello,\n\nAttached is your detailed cost intelligence report.\n\n– Intelligent Cost Analyzer Team")
    msg.add_attachment(report_bytes, maintype="application", subtype="pdf", filename="Cost_Analysis_Report.pdf")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender_email, sender_password)
        smtp.send_message(msg)

if st.button("📧 Email Me the Report"):
    with st.spinner("Sending report..."):
        try:
            send_report_email(user_email, pdf_report)
            st.success(f"✅ Report sent successfully to {user_email}")
        except Exception as e:
            st.error(f"❌ Failed to send email: {e}")

# -----------------------------------------------------------
# INSIGHTS SECTION
# -----------------------------------------------------------
st.markdown("""
---
## 🧩 Project Summary

This project helps visualize and understand cloud costs more effectively.
It combines forecasting, anomaly detection, CEI measurement, and comparative analytics
to support transparent, data-driven cost management.

- **Forecasting**: Predicts expected spending for the next 30 days.  
- **Anomaly Detection**: Flags unexpected cost spikes.  
- **CEI (Cost Efficiency Index)**: Measures how efficient current spending is compared to forecasted values.  
- **Multi-App Comparison**: Highlights which services contribute most to total cost.  
- **Report Export**: Generates a well-formatted PDF for download or email.

💡 *Demonstrates the fusion of data analytics and intelligent forecasting for cloud cost governance.*
""")
