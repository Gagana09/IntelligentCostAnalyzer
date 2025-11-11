import os
from msal import ConfidentialClientApplication
from dotenv import load_dotenv

# Load secrets from .env
load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

authority = f"https://login.microsoftonline.com/{TENANT_ID}"
scope = ["https://management.azure.com/.default"]

# Create confidential client app
app = ConfidentialClientApplication(
    CLIENT_ID,
    authority=authority,
    client_credential=CLIENT_SECRET
)

# Acquire token
result = app.acquire_token_for_client(scopes=scope)

if "access_token" in result:
    print("✅ Access token acquired successfully!")
    # Optional: print first 50 chars of token
    print(result["access_token"][:50] + "...")
else:
    print("❌ Error acquiring token:")
    print(result)
