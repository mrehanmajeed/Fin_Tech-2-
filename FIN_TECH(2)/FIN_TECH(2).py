# ==============================================================
# Bank vs Ledger Reconciliation - Optimized PDF Compliant Version
# Author: Muhammad Rehan Majeed
# Description:
#   Reads Bank & Ledger Excel files, cleans them, runs:
#     - Direct Matching (sign-sensitive & absolute)
#     - Subset-Sum Matching (Dynamic Programming for small sets)
#     - Genetic Algorithm (for large sets)
#     - Greedy Unique 1:1 Assignment
#   Produces Excel & PNG outputs for all steps.
# ==============================================================

import pandas as pd
import numpy as np
import itertools
import time
import random
from decimal import Decimal, ROUND_HALF_UP
from difflib import SequenceMatcher
import matplotlib.pyplot as plt
from time import time as now
from tqdm import tqdm

# ------------------------------
# 1. CONFIGURATION
# ------------------------------
BANK_FILE   = "KH_Bank.XLSX"
LEDGER_FILE = "Customer_Ledger_Entries_FULL.xlsx"
MAX_COMB_SIZE = 18  
DP_THRESHOLD_TXNS = 100      # Only run DP if <= 100 transactions
MAX_RUNTIME_PER_TARGET = 1.5 # seconds timeout per target

# ------------------------------
# 2. HELPER FUNCTIONS
# ------------------------------

def normalize_amount_to_cents(x):
    """Convert to integer cents."""
    if pd.isna(x):
        return None
    try:
        s = str(x).strip()
        neg = False
        if s.startswith("(") and s.endswith(")"):
            neg = True
            s = s[1:-1]
        s = s.replace(",", "").replace(" ", "")
        val = Decimal(s)
        if neg:
            val = -val
        return int(val.scaleb(2).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except:
        return None

def find_date_column(cols):
    for cand in ["date", "txn date", "value date", "posting date", "transaction date"]:
        for col in cols:
            if cand in col.lower():
                return col
    return None

def standardize_text(x):
    return str(x).strip() if pd.notna(x) else ""

def fuzzy_score(a, b):
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# ------------------------------
# 3. LOAD & CLEAN DATA
# ------------------------------

def load_transactions(path):
    dfs = []
    xl = pd.ExcelFile(path)
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        df.columns = [str(c).strip() for c in df.columns]

        date_col = find_date_column(df.columns)
        date_series = pd.to_datetime(df[date_col], errors="coerce") if date_col else pd.NaT

        deb_cols = [c for c in df.columns if "debit" in c.lower()]
        cre_cols = [c for c in df.columns if "credit" in c.lower()]
        if deb_cols or cre_cols:
            debit  = df[deb_cols[0]].apply(normalize_amount_to_cents) if deb_cols else 0
            credit = df[cre_cols[0]].apply(normalize_amount_to_cents) if cre_cols else 0
            amount_cents = credit.sub(debit, fill_value=0)
        else:
            amt_cols = [c for c in df.columns if "amount" in c.lower()]
            amount_cents = df[amt_cols[0]].apply(normalize_amount_to_cents) if amt_cols else pd.Series([None]*len(df))

        desc_col = None
        for cand in ["description", "details", "narration", "remarks"]:
            for c in df.columns:
                if cand in c.lower():
                    desc_col = c
                    break
            if desc_col:
                break
        description = df[desc_col].apply(standardize_text) if desc_col else ""

        out = pd.DataFrame({
            "uid": [f"TXN-{sheet}-{i+1}" for i in range(len(df))],
            "amount_cents": amount_cents,
            "description": description,
            "date": date_series
        })
        dfs.append(out)
    return pd.concat(dfs, ignore_index=True).dropna(subset=["amount_cents"])

def load_targets(path):
    dfs = []
    xl = pd.ExcelFile(path)
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        df.columns = [str(c).strip() for c in df.columns]

        date_col = find_date_column(df.columns)
        date_series = pd.to_datetime(df[date_col], errors="coerce") if date_col else pd.NaT

        amt_col = None
        for c in df.columns:
            if "amount" in c.lower():
                amt_col = c
                break
        if amt_col is None:
            continue

        ref_col = None
        for c in df.columns:
            if any(k in c.lower() for k in ["reference", "ref", "invoice", "doc"]):
                ref_col = c
                break

        out = pd.DataFrame({
            "uid": [f"TGT-{sheet}-{i+1}" for i in range(len(df))],
            "target_amount_cents": df[amt_col].apply(normalize_amount_to_cents),
            "reference_id": df[ref_col].apply(standardize_text) if ref_col else "",
            "date": date_series
        })
        dfs.append(out)
    return pd.concat(dfs, ignore_index=True).dropna(subset=["target_amount_cents"])

# ------------------------------
# 4. MATCHING FUNCTIONS
# ------------------------------

def direct_match(transactions, targets):
    return targets.merge(transactions, left_on="target_amount_cents", right_on="amount_cents", how="inner")

def direct_match_abs(transactions, targets):
    tx = transactions.copy()
    tg = targets.copy()
    tx["abs_amount_cents"] = tx["amount_cents"].abs()
    tg["abs_target_amount_cents"] = tg["target_amount_cents"].abs()
    return tg.merge(tx, left_on="abs_target_amount_cents", right_on="abs_amount_cents", how="inner")

def subset_sum_dp(amounts, target):
    dp = {0: []}
    for i, amt in enumerate(amounts):
        for s, comb in list(dp.items()):
            ns = s + amt
            if ns not in dp:
                dp[ns] = comb + [i]
            if ns == target:
                return dp[ns]
    return None

def ga_exact_match(amounts, target, pop_size=50, generations=80, mutation_rate=0.05):
    if not amounts or target is None:
        return None

    def fitness(ind):
        s = sum(amounts[i] for i in range(len(ind)) if ind[i])
        return -abs(s - target)

    population = [[random.choice([0, 1]) for _ in range(len(amounts))] for _ in range(pop_size)]

    for _ in range(generations):
        fits = [fitness(ind) for ind in population]
        if max(fits) == 0:
            return [i for i, bit in enumerate(population[fits.index(max(fits))]) if bit]

        # Shift weights to be strictly positive
        min_fit = min(fits)
        shifted_weights = [(f - min_fit) + 1 for f in fits]  # ensures all > 0

        selected = random.choices(population, weights=shifted_weights, k=pop_size // 2)

        children = []
        for _ in range(pop_size // 2):
            p1, p2 = random.sample(selected, 2)
            point = random.randint(1, len(amounts) - 1)
            child = p1[:point] + p2[point:]
            if random.random() < mutation_rate:
                idx = random.randint(0, len(amounts) - 1)
                child[idx] = 1 - child[idx]
            children.append(child)

        population = selected + children

    return None

# ------------------------------
# 5. RUN PIPELINE (Optimized)
# ------------------------------

transactions = load_transactions(BANK_FILE)
targets = load_targets(LEDGER_FILE)
transactions.to_excel("clean_transactions.xlsx", index=False)
targets.to_excel("clean_targets.xlsx", index=False)

# Direct matches
matches_sign = direct_match(transactions, targets)
matches_abs = direct_match_abs(transactions, targets)

matched_target_uids = set(matches_abs["uid_x"].unique())
remaining_targets = targets[~targets["uid"].isin(matched_target_uids)]

print(f"Direct matches found: {len(matched_target_uids)}, remaining: {len(remaining_targets)}")

subset_dp = []
subset_ga = []

for _, tgt in tqdm(remaining_targets.iterrows(), total=len(remaining_targets), desc="Matching Remaining Targets"):
    amts = transactions["amount_cents"].abs().tolist()
    idxs_dp = None

    if len(amts) <= DP_THRESHOLD_TXNS:
        start_t = now()
        idxs_dp = subset_sum_dp(amts, abs(tgt["target_amount_cents"]))
        if now() - start_t > MAX_RUNTIME_PER_TARGET:
            idxs_dp = None  # Timeout

    if idxs_dp:
        subset_dp.append({"target_uid": tgt["uid"], "txn_uids": [transactions.iloc[i]["uid"] for i in idxs_dp], "method": "dp"})
    else:
        idxs_ga = ga_exact_match(amts, abs(tgt["target_amount_cents"]))
        if idxs_ga:
            subset_ga.append({"target_uid": tgt["uid"], "txn_uids": [transactions.iloc[i]["uid"] for i in idxs_ga], "method": "ga_exact"})

subset_dp_df = pd.DataFrame(subset_dp)
subset_ga_df = pd.DataFrame(subset_ga)

# Greedy Unique Assignment
unique_assignments = []
used_txn = set()
for _, tgt in targets.iterrows():
    cands = matches_abs[matches_abs["uid_x"] == tgt["uid"]]
    for _, row in cands.iterrows():
        if row["uid_y"] not in used_txn:
            used_txn.add(row["uid_y"])
            unique_assignments.append({"target_uid": tgt["uid"], "txn_uids": [row["uid_y"]], "method": "direct_abs"})
            break

unique_df = pd.DataFrame(unique_assignments)

# Save outputs
matches_sign.to_excel("matches_direct_sign.xlsx", index=False)
matches_abs.to_excel("matches_direct_abs.xlsx", index=False)
subset_dp_df.to_excel("matches_subset_exact_dp.xlsx", index=False)
subset_ga_df.to_excel("matches_subset_exact_ga.xlsx", index=False)
unique_df.to_excel("unique_assignment.xlsx", index=False)

# Benchmark
def benchmark():
    sizes = [5, 10, 15, 20]
    results = []
    for size in sizes:
        sample = transactions.head(size)["amount_cents"].abs().tolist()
        target_val = sum(sample[:2])
        t0 = time.time(); subset_sum_dp(sample, target_val); t_dp = time.time()-t0
        t0 = time.time(); ga_exact_match(sample, target_val); t_ga = time.time()-t0
        results.append({"size": size, "dp_s": t_dp, "ga_s": t_ga})
    return pd.DataFrame(results)

bench_df = benchmark()
bench_df.to_excel("performance_benchmark.xlsx", index=False)

plt.plot(bench_df["size"], bench_df["dp_s"], marker="o", label="DP")
plt.plot(bench_df["size"], bench_df["ga_s"], marker="o", label="GA Exact")
plt.xlabel("Candidate Count"); plt.ylabel("Time (s)")
plt.title("Subset Sum Performance"); plt.legend()
plt.savefig("subset_sum_benchmark.png"); plt.close()

# ------------------------------
# 6. SUMMARY
# ------------------------------
print(f"Loaded: transactions={len(transactions)}, targets={len(targets)}")
print("=== MATCH RESULTS ===")
print(f"Direct sign matches: {len(matches_sign)}")
print(f"Direct abs matches : {len(matches_abs)}")
print(f"Subset DP exact    : {len(subset_dp_df)}")
print(f"GA exact matches   : {len(subset_ga_df)}")
print(f"Unique 1:1 assigned: {len(unique_df)}")
print("Artifacts saved: clean data, matches, subset results, benchmarks, PNG chart")