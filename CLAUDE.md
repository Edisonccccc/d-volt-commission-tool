# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py

# The app opens at http://localhost:8501
```

## Architecture

Single-process Streamlit app. No separate backend server.

```
app.py              # Entry point: calls init_db(), sidebar nav, dynamically imports pages
database.py         # SQLAlchemy models + SQLite (commission.db) + init_db() seeding
calculator.py       # Pure functions — no DB imports. All commission math lives here.
pages/
  settings.py       # Edit commission brackets
  employees.py      # Employee CRUD
  cycles.py         # Commission cycles per employee
  transactions.py   # Transaction entry/editing per cycle
  statement.py      # Computed statement view + Excel export
```

## Commission Calculation Logic

Defined in `calculator.py`. Key entry point: `compute_statement(transactions, brackets, threshold)`.

**Tiered marginal brackets** (seeded from xlsx, editable in Settings):
- $0–$1M: 2%, $1M–$3M: 3%, $3M–$7M: 4%, above $7M: 5%

**Per-transaction flow:**
1. Net Revenue = Collection − Sales Tax − Referral Fee − Approved Sales Exp
2. Calc Revenue = Net Revenue × Commission Weight
3. Accumulated Revenue = running sum across all transactions in the cycle
4. Commission Earned = incremental marginal commission on [prev_accumulated → new_accumulated]
5. **Threshold rule**: no commission is paid until accumulated revenue exceeds `CommissionCycle.commission_threshold`. Once crossed, commission is earned retroactively on all revenue from $0 (handled in `_marginal_commission` + catch-up logic in `compute_statement`).
6. Sales Expense Allowance = 0.001 × Qty

## Database

SQLite file: `commission.db` (created on first run). Use `get_session()` as a context manager. All computed columns are derived at runtime — only raw inputs are stored.

`CommissionCycle.commission_threshold` = `applicable_threshold − threshold_carryforward`.

## Verification

Enter the sample ABC transactions from `CommissionStatement_2026v2.xlsx` and verify:
- $50k net → $1,000 commission earned (2% × $50k)
- +$500k → $10,000 earned (running total $11,000)
- +$1M → $25,500 earned (running total $36,500)
- +$2.5M → $85,500 earned (running total $122,000)
