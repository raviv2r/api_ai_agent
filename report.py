import pandas as pd

def save_report(data):
    df = pd.DataFrame([data])
    df.to_csv("api_report.csv", mode="a", index=False, header=False)