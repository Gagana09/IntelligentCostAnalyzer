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
    }

    /* Fade animation */
    @keyframes fadeIn {
        0% {opacity: 0; transform: translateY(-20px);}
        100% {opacity: 1; transform: translateY(0);}
    }

    .landing-title {
        font-size: 52px;
        font-weight: 800;
        margin-bottom: 15px;
        text-shadow: 0 2px 5px rgba(0,0,0,0.3);
    }

    .landing-subtitle {
        font-size: 20px;
        color: #D6EAF8;
        margin-bottom: 50px;
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
            <div class="landing-subtitle">Select how you want to explore your cloud costs</div>
        </div>
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

    uploaded_file = st.file_uploader("📂 Upload your cost data (CSV)", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.success("✅ File uploaded successfully!")
    else:
        st.info("No file uploaded — using demo data.")
        df = pd.read_csv("synthetic_cost_data.csv")

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

    if st.button("⬅️ Back to Home"):
        st.session_state.page = "landing"
        st.rerun()

    st.caption(f"👤 Logged in as Admin ({ADMIN_EMAIL})")

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
        rows = [{"Date": str(int(r[1])), "AppName": r[2], "Cost": r[0]} for r in response.rows]
        df = pd.DataFrame(rows)
        df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d")
        return df

    df = fetch_cost_data()
    st.success("✅ Live Azure cost data retrieved successfully!")

    selected_app = st.sidebar.selectbox("Select Resource Group", sorted(df["AppName"].unique()))
    filtered_df = df[df["AppName"] == selected_app].copy().sort_values("Date")

    st.subheader(f"📈 Cost Trend for {selected_app}")
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(x="Date", y="Cost", data=filtered_df, marker="o", color="royalblue", ax=ax)
    st.pyplot(fig)

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
