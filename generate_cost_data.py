import random
import json

# Define applications and microservices
apps = {
    "AuthAPI": ["LoginService", "TokenService"],
    "AnalyticsService": ["DataIngest", "ReportService"],
    "DatabaseCluster": ["DBCluster1", "DBCluster2"],
    "FrontendApp": ["WebApp", "MobileApp"]
}

# Generate simulated cost data for 30 days
cost_data = {}

for app, services in apps.items():
    cost_data[app] = {}
    for service in services:
        daily_costs = [round(random.uniform(100, 500), 2) for _ in range(30)]
        cost_data[app][service] = daily_costs

# Save to JSON
with open("sample_cost_data.json", "w") as f:
    json.dump(cost_data, f, indent=4)

print("Sample cost data generated and saved as sample_cost_data.json")
