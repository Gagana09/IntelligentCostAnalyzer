from azure.identity import DeviceCodeCredential
from azure.mgmt.costmanagement import CostManagementClient
import json

# -----------------------------------------------------------
# Azure Credentials (interactive login version)
# -----------------------------------------------------------
TENANT_ID = "cafd2576-1a76-444b-8308-df607f8b743d"
CLIENT_ID = "236d9374-5836-422f-a2d9-a2fc302e0ee9"
SUBSCRIPTION_ID = "d6e4b3f9-95f1-4234-9b66-046747c96c0d"

print("🔐 Authenticating using interactive device login...")

# This opens a browser or provides a URL+code for login
credential = DeviceCodeCredential(client_id=CLIENT_ID, tenant_id=TENANT_ID)

# Create cost management client
cost_client = CostManagementClient(credential)

# Scope: Subscription-level query
scope = f"/subscriptions/{SUBSCRIPTION_ID}"

print("🔍 Fetching Azure Cost Data...")

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

# Print response nicely
print(json.dumps(response.as_dict(), indent=2))
