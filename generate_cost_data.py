import pandas as pd
import numpy as np
from datetime import datetime, timedelta

apps = ["AuthAPI", "AnalyticsService", "DatabaseCluster", "FrontendApp", "PaymentGateway"]
days = 60

data = []
for app in apps:
    base_cost = np.random.randint(2000, 4000)
    for i in range(days):
        date = datetime.today() - timedelta(days=days - i)
        daily_cost = base_cost * (1.03 ** i) + np.random.randint(-100, 100)
        data.append([date.strftime("%Y-%m-%d"), app, int(daily_cost)])

df = pd.DataFrame(data, columns=["Date", "AppName", "Cost"])
df.to_csv("synthetic_cost_data_growth.csv", index=False)
print("📈 synthetic_cost_data_growth.csv generated with exponential trend")
