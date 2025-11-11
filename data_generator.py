import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Settings
apps = ["AuthAPI", "AnalyticsService", "DatabaseCluster", "FrontendApp", "PaymentGateway"]
days = 60  # Last 60 days of data

data = []

for app in apps:
    cost = np.random.randint(2000, 10000)  # starting cost
    for i in range(days):
        date = datetime.today() - timedelta(days=days - i)
        daily_cost = cost + np.random.randint(-500, 500)
        data.append([date.strftime("%Y-%m-%d"), app, max(daily_cost, 0)])

df = pd.DataFrame(data, columns=["date", "application", "cost"])

# Save to CSV (optional, but you can also read directly in memory)
df.to_csv("synthetic_cost_data.csv", index=False)

print("Synthetic cost data generated!")
