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
from auth_helpers import create_user, find_user_by_email, check_password

# Optional Azure Advisor Helper
try:
    from advisor_helper import get_advisor_recommendations
except:
    def get_advisor_recommendations(subscription_id): return []

# -----------------------------------------------------------
# GLOBAL CONFIGURATION
# -----------------------------------------------------------
st.set_page_config(page_title="💰 Intelligent Cost Analyzer", layout="wide")
plt.style.use('seaborn-v0_8-darkgrid')

ADMIN_EMAIL = "supriya21404@gmail.com"
SENDER_EMAIL = "acharyagagana@gmail.com"
SENDER_PASSWORD = "ihnwddcbnscgnmmf"
SUBSCRIPTION_ID = "d6e4b3f9-95f1-4234-9b66-046747c96c0d"

# -----------------------------------------------------------
# SESSION STATE DEFAULTS
# -----------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "landing"
if "user" not in st.session_state:
    st.session_state.user = None

# -----------------------------------------------------------
# LANDING PAGE
# -----------------------------------------------------------
if st.session_state.page == "landing":
    st.markdown("""
    <style>
    /* Hide Streamlit's default header/footer */
    header, footer {visibility: hidden;}
    main .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100%;
    }

    /* Landing container */
    .landing-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100vh;
        width: 100vw;
        background: radial-gradient(circle at top, #001F3F, #111);
        color: white;
        text-align: center;
        animation: fadeIn 1.2s ease-in-out;
        margin:10px;
    }

    /* Fade animation */
    @keyframes fadeIn {
        0% {opacity: 0; transform: translateY(-20px);}
        100% {opacity: 1; transform: translateY(0);}
    }

    .landing-title {
        font-size: 52px;
        font-weight: 800;
        margin-bottom: 5px;
        text-shadow: 0 2px 5px rgba(0,0,0,0.3);
    }

    .landing-subtitle {
        font-size: 20px;
        color: #D6EAF8;
        margin-bottom: 10px;
    }

    /* Buttons */
    .button-row {
        display: flex;
        justify-content: center;
        gap: 30px;
        width: 100%;
        max-width: 600px;
    }

    div[data-testid="stHorizontalBlock"] {
        justify-content: center;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .landing-title {
            font-size: 36px;
        }
        .landing-subtitle {
            font-size: 16px;
        }
        .button-row {
            flex-direction: column;
            align-items: center;
            gap: 20px;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    # ---- HTML Header Section ----
    st.markdown("""
    <div class="landing-container">
    <div class="landing-title">💰 Intelligent Cost Analyzer</div>
    
    <p style="font-size:20px; max-width:900px; margin:auto; color:#D6EAF8; line-height:1.6;">
    The Intelligent Cost Analyzer helps organizations understand, analyze, and 
    optimize their cloud spending.  
    <br><br>
    🔹  <b>Azure Subscription Insights</b> provides real-time cost analytics directly from your Azure account — 
    including usage trends, forecasting, anomaly detection, cost efficiency scoring, and optimization recommendations.  
    <br><br>
    🔹 <b>CSV-Based Analysis</b> allows users to upload their own application-wise cost data to visualize trends, 
    predict future costs, detect irregular spikes, and generate summaries instantly.  
    <br><br>
    The system is designed for students, developers, and cloud administrators who want 
    a smart and interactive way to track cloud expenditure and make data-driven 
    decisions.
    <div class="landing-subtitle">Select how you want to explore your cloud costs</div>
    </p>

        
    """, unsafe_allow_html=True)

    # ---- Streamlit Buttons Section ----
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        if st.button("🌐 Azure Subscription Insights", use_container_width=True):
            st.session_state.page = "azure_login"
            st.rerun()
    with col2:
        if st.button("📁 Upload CSV for Analysis", use_container_width=True):
            st.session_state.page = "user_login"
            st.rerun()

    st.stop()


# -----------------------------------------------------------
# LOGIN / REGISTER PAGE
# -----------------------------------------------------------
def show_login_page(is_admin=False):
    st.markdown("<h2 style='text-align:center;'>🔑 Login</h2>", unsafe_allow_html=True)

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "landing"
        st.rerun()

    if is_admin:
        st.subheader("👩‍💼 Admin Login (Azure Subscription Mode)")
        email = st.text_input("Admin Email")
        password = st.text_input("Password", type="password")
        if st.button("Login as Admin"):
            if email.strip().lower() == ADMIN_EMAIL.lower() and password.strip() == "admin123":
                st.session_state.user = {"email": ADMIN_EMAIL, "name": "Admin"}
                st.session_state.page = "azure_mode"
                st.rerun()
            else:
                st.error("Invalid admin credentials.")
        st.stop()
    else:
        mode = st.radio("Choose Mode", ["Login", "Register"], horizontal=True)
        if mode == "Register":
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
                    st.session_state.page = "csv_mode"
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
        st.stop()

# -----------------------------------------------------------
# USER MODE — CSV BASED COST ANALYSIS
# -----------------------------------------------------------
def csv_analysis_app():
    st.title("📊 Intelligent Cost Analyzer – CSV Mode")

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "landing"
        st.rerun()

    user_email = st.session_state.user["email"]
    st.caption(f"👤 Logged in as: {user_email}")
    
    st.markdown("""
    ### 📌 CSV Format Requirements  
    Please upload a CSV file in the following format:

    | **Date** | **AppName** | **Cost** |
    |----------|-------------|----------|
    | 2024-01-01 | HRPortal | 120 |
    | 2024-01-02 | HRPortal | 135 |
    | 2024-01-03 | PayrollApp | 90 |

    #### ✔ Required Columns  
    - **Date** → Accepted names: `Date`, `date`  
    - **AppName** → Accepted names: `AppName`, `appname`, `application`  
    - **Cost** → Accepted names: `Cost`, `cost`

    #### ✔ Accepted Date Formats  
    - `YYYY-MM-DD`  
    - `YYYY/MM/DD`  
    - `DD-MM-YYYY`  
    - `DD/MM/YYYY`

    #### ⚠ Important Notes  
    - All 3 columns are **mandatory**  
    - Extra columns are allowed, but the 3 key columns must be present  
    - Rows with invalid or empty dates will be skipped  
    """)

    uploaded_file = st.file_uploader("📂 Upload your cost data (CSV)", type=["csv"])
    # ❌ No demo data
    # ✔ Force user to upload CSV
    if uploaded_file is None:
        st.warning("⚠ Please upload a CSV file to continue.")
        st.stop()

    df = pd.read_csv(uploaded_file)
    st.success("✅ File uploaded successfully!")


    df.columns = [col.strip().lower() for col in df.columns]
    rename_map = {"date": "Date", "application": "AppName", "appname": "AppName", "cost": "Cost"}
    df.rename(columns=rename_map, inplace=True)
    if not {"Date", "AppName", "Cost"}.issubset(df.columns):
        st.error("❌ CSV must have columns: Date, AppName, and Cost")
        st.stop()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df.dropna(subset=["Date"], inplace=True)

    selected_app = st.sidebar.selectbox("Select Application", sorted(df["AppName"].unique()))
    filtered_df = df[df["AppName"] == selected_app].copy().sort_values("Date")

    # Trend
    st.subheader(f"📈 Cost Trend for {selected_app}")
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(x="Date", y="Cost", data=filtered_df, marker="o", color="deepskyblue", ax=ax)
    st.pyplot(fig)

    # Forecasting
    st.subheader("🔮 Forecasting Next 30 Days")
    if len(filtered_df) > 5:
        forecast_df = filtered_df[["Date", "Cost"]].rename(columns={"Date": "ds", "Cost": "y"})
        model = Prophet(daily_seasonality=True)
        model.fit(forecast_df)
        future = model.make_future_dataframe(periods=30)
        forecast = model.predict(future)
        next_month = forecast.tail(30)["yhat"].mean()
        st.success(f"📅 Predicted average cost for next 30 days: ₹{int(next_month)}")
    else:
        next_month = filtered_df["Cost"].mean()

    # Anomaly Detection
    st.subheader("⚠️ Anomaly Detection")
    mean_cost, std_cost = filtered_df["Cost"].mean(), filtered_df["Cost"].std()
    filtered_df["Anomaly"] = np.abs(filtered_df["Cost"] - mean_cost) > 2 * std_cost
    if filtered_df["Anomaly"].any():
        st.error("🚨 Detected anomalies!")
        st.dataframe(filtered_df[filtered_df["Anomaly"]][["Date", "Cost"]])
    else:
        st.success("✅ No anomalies detected.")

    # CEI
    avg_cost = filtered_df["Cost"].mean()
    if next_month > 0 and avg_cost > 0:
        cei = round((avg_cost / next_month) * 100, 2)
        st.metric("📏 Cost Efficiency Index", f"{cei}%")

    # Summary
    st.subheader("🏗️ Application-Wise Cost Summary")
    app_summary = df.groupby("AppName")["Cost"].agg(["sum", "min", "max", "mean"]).reset_index()
    st.dataframe(app_summary)

# -----------------------------------------------------------
# ADMIN MODE — AZURE SUBSCRIPTION INSIGHTS
# -----------------------------------------------------------
def azure_admin_app():
    st.title("💼 Azure Subscription Cost Insights (Admin Mode)")
    st.caption(f"👤 Logged in as Admin ({ADMIN_EMAIL})")

    # ✅ BACK TO HOME BUTTON
    if st.button("⬅️ Back to Home"):
        st.session_state.page = "landing"
        st.rerun()

    @st.cache_data
    def fetch_cost_data():
        st.info("🔐 Authenticating with Azure... Please approve device login.")
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

    df = fetch_cost_data()
    st.success("✅ Live Azure cost data retrieved successfully!")

    selected_app = st.sidebar.selectbox("Select Resource Group", sorted(df["AppName"].unique()))
    filtered_df = df[df["AppName"] == selected_app].copy().sort_values("Date")

    # -----------------------------------------------------------
    # COST TREND
    # -----------------------------------------------------------
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
    # COST SUMMARY TABLE
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
    # EMAIL AUTOMATED REPORT
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

# -----------------------------------------------------------
# MAIN CONTROLLER
# -----------------------------------------------------------
def main():
    if st.session_state.page == "user_login":
        show_login_page(is_admin=False)
    elif st.session_state.page == "azure_login":
        show_login_page(is_admin=True)
    elif st.session_state.page == "csv_mode":
        csv_analysis_app()
    elif st.session_state.page == "azure_mode":
        azure_admin_app()
    else:
        st.session_state.page = "landing"
        st.rerun()

if __name__ == "__main__":
    main()
