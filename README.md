# Bank vs Ledger Reconciliation

This project reconciles transactions between a bank statement and a customer ledger.  
It is implemented in **Python** using **Jupyter Notebook**.

## 📌 Features
- **Data Preprocessing**
  - Reads all sheets from Excel files
  - Cleans and normalizes amounts, descriptions, and dates
  - Handles debit/credit and amount-only formats
- **Matching Algorithms**
  - Direct match (sign-sensitive)
  - Direct match (absolute values)
  - Subset-sum match (Brute Force)
  - Subset-sum match (Dynamic Programming)
  - Genetic Algorithm (Exact Match)
  - Greedy Unique 1-to-1 Assignment
- **Fuzzy Matching** (for description similarity scoring)
- **Performance Benchmarking**
  - Execution time comparison between Brute Force, DP, and GA
- **Outputs**
  - Cleaned data files
  - All match results in Excel format
  - Benchmark chart in PNG format

## 📂 Input Files
Place the following files in the **same directory** as your Jupyter Notebook:
- `KH_Bank.XLSX` — Bank transactions
- `Customer_Ledger_Entries_FULL.xlsx` — Ledger entries


## Create a virtual environment (optional but recommended):
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows

## Install dependencies:
pandas==2.2.2
numpy==1.26.4
matplotlib==3.8.4
openpyxl==3.1.2
xlrd==2.0.1
jupyter==1.0.0

## Run in Jupyter Notebook or CMD:
jupyter notebook

CMD Command:
python FIN_TECH(2).py

## 🛠 Switching to Full BF + DP Mode

By default, the script skips Brute Force and limits DP to small datasets for speed.
If you want full exhaustive matching:

Open the script and find:
DP_THRESHOLD_TXNS = 100

Change it to:

DP_THRESHOLD_TXNS = 999999

In GA, increase generations:

ga_exact_match(..., generations=300)

⚠️ Note: This will significantly increase runtime for large datasets (could take hours).

🖼 Outputs

The script generates:

clean_transactions.xlsx — Cleaned bank statement data

clean_targets.xlsx — Cleaned ledger data

matches_direct_sign.xlsx

matches_direct_abs.xlsx

matches_subset_exact_dp.xlsx (DP results)

matches_subset_exact_ga.xlsx (GA results)

unique_assignment.xlsx

performance_benchmark.xlsx

subset_sum_benchmark.png

⚡ GPU/Performance Tip

If your machine is slow:

Keep default settings (fast mode)

Lower generations in GA for faster runs:

ga_exact_match(..., generations=50)

Increase DP_THRESHOLD_TXNS only if you have time and processing power.

📌 Author
Muhammad Rehan Majeed






