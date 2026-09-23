"""Join Client_Anomaly_Report.csv to the Opportunities Excel. Print unmatched rates. No invented types."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
csv_path = ROOT / "Client_Anomaly_Report.csv"
xlsx = ROOT / "api" / "data" / "opportunities.xlsx"
if not xlsx.exists():
    xlsx = ROOT / "NA_Synthetic_SFDC_Opportunities 1.xlsx"

report = pd.read_csv(csv_path)
opps = pd.read_excel(xlsx, sheet_name="Opportunities")

print("report_rows", len(report))
print("types")
print(report.groupby(["AnomalyCategory", "AnomalyType"]).size().sort_values(ascending=False).to_string())
print("entity", report["EntityType"].value_counts().to_string())
print("severity_minmax", report["Severity"].min(), report["Severity"].max())
print("demo_true", int(report["DemoPriority"].astype(str).str.lower().isin(["true", "1"]).sum()))

codes = set(opps["OpportunityCode"].astype(str))
accounts = set(opps["AccountCode"].astype(str))
owners = set(opps["OpportunityOwnerFullName"].astype(str))
industries = set(opps["AccountIndustry"].astype(str))

opp_rows = report[report["EntityType"] == "Opportunity"]
acct_rows = report[report["EntityType"] == "Account"]
rep_rows = report[report["EntityType"] == "Rep"]
ind_rows = report[report["EntityType"] == "Industry"]

print("opp_in_excel", int(opp_rows["DealId"].astype(str).isin(codes).sum()), "/", len(opp_rows))
print("acct_in_excel", int(acct_rows["DealId"].astype(str).isin(accounts).sum()), "/", len(acct_rows))
print("rep_in_excel", int(rep_rows["DealId"].astype(str).isin(owners).sum()), "/", len(rep_rows))
print("ind_in_excel", int(ind_rows["DealId"].astype(str).isin(industries).sum()), "/", len(ind_rows))

miss_opp = opp_rows[~opp_rows["DealId"].astype(str).isin(codes)]
print("missing_opp", len(miss_opp))
if len(miss_opp):
    print(miss_opp[["AnomalyId", "DealId", "Deal"]].head(10).to_string(index=False))

# spot-check ANM-00280 vs Excel
row = report[report["AnomalyId"] == "ANM-00280"].iloc[0]
code = str(row["DealId"])
lines = opps[opps["OpportunityCode"].astype(str) == code]
print("ANM-00280 Deal", row["Deal"])
print("ANM-00280 Rep", row["RepName"], "DealValue", row["DealValue"])
print("excel name", lines["OpportunityName"].iloc[0] if len(lines) else None)
print("excel owner", lines["OpportunityOwnerFullName"].iloc[0] if len(lines) else None)
print("excel gp_sum", float(lines["SFDC_ACV_Gp"].sum()) if len(lines) else None)
print("excel rev_sum", float(lines["SFDC_ACV_Revenue"].sum()) if len(lines) else None)
