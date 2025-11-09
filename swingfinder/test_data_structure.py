"""
Test to see the actual data structure from Tiingo
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
TIINGO_TOKEN = os.getenv("TIINGO_TOKEN", "")

ticker = "AAPL"
url = f"https://api.tiingo.com/tiingo/fundamentals/{ticker.lower()}/statements"
headers = {"Authorization": f"Token {TIINGO_TOKEN}"}

response = requests.get(url, headers=headers, timeout=10)
data = response.json()

print("=" * 60)
print("FULL DATA STRUCTURE FOR AAPL")
print("=" * 60)
print()

if isinstance(data, list) and len(data) > 0:
    latest = data[0]
    
    print("Top-level keys:")
    print(json.dumps(list(latest.keys()), indent=2))
    print()
    
    print("=" * 60)
    print("STATEMENT DATA STRUCTURE")
    print("=" * 60)
    print()
    
    statement_data = latest.get("statementData", {})
    
    print("Statement Data keys:")
    print(json.dumps(list(statement_data.keys()), indent=2))
    print()
    
    # Income Statement
    if "incomeStatement" in statement_data:
        print("=" * 60)
        print("INCOME STATEMENT")
        print("=" * 60)
        income = statement_data["incomeStatement"]
        print(f"Type: {type(income)}")
        print(f"Length: {len(income)}")
        print()
        print("Available data codes:")
        for item in income[:10]:  # First 10
            print(f"  - {item.get('dataCode')}: {item.get('value')}")
        print()
    
    # Balance Sheet
    if "balanceSheet" in statement_data:
        print("=" * 60)
        print("BALANCE SHEET")
        print("=" * 60)
        balance = statement_data["balanceSheet"]
        print(f"Type: {type(balance)}")
        print(f"Length: {len(balance)}")
        print()
        print("Available data codes:")
        for item in balance[:10]:  # First 10
            print(f"  - {item.get('dataCode')}: {item.get('value')}")
        print()
    
    # Cash Flow
    if "cashFlow" in statement_data:
        print("=" * 60)
        print("CASH FLOW")
        print("=" * 60)
        cash = statement_data["cashFlow"]
        print(f"Type: {type(cash)}")
        print(f"Length: {len(cash)}")
        print()
        print("Available data codes:")
        for item in cash[:10]:  # First 10
            print(f"  - {item.get('dataCode')}: {item.get('value')}")
        print()
    
    print("=" * 60)
    print("KEY METRICS WE NEED")
    print("=" * 60)
    print()
    
    # Find the metrics we need
    income_statement = {item['dataCode']: item['value'] for item in statement_data.get('incomeStatement', [])}
    balance_sheet = {item['dataCode']: item['value'] for item in statement_data.get('balanceSheet', [])}
    
    print("Looking for:")
    print(f"  Revenue: {income_statement.get('revenue', 'NOT FOUND')}")
    print(f"  Net Income: {income_statement.get('netIncComStock', 'NOT FOUND')}")
    print(f"  Total Assets: {balance_sheet.get('totalAssets', 'NOT FOUND')}")
    print(f"  Total Equity: {balance_sheet.get('totalEquity', 'NOT FOUND')}")
    print(f"  Total Debt: {balance_sheet.get('totalDebt', 'NOT FOUND')}")
    print(f"  Current Assets: {balance_sheet.get('currentAssets', 'NOT FOUND')}")
    print(f"  Current Liabilities: {balance_sheet.get('currentLiabilities', 'NOT FOUND')}")
    print()
    
    print("=" * 60)
    print("ALL INCOME STATEMENT DATA CODES")
    print("=" * 60)
    for item in statement_data.get('incomeStatement', []):
        print(f"  {item.get('dataCode')}")
    print()
    
    print("=" * 60)
    print("ALL BALANCE SHEET DATA CODES")
    print("=" * 60)
    for item in statement_data.get('balanceSheet', []):
        print(f"  {item.get('dataCode')}")

print()
print("TEST COMPLETE!")

