# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app (Python 3.9 on macOS)
/Users/edison/Library/Python/3.9/bin/streamlit run app.py

# The app opens at http://localhost:8501 (or 8502 if port is taken)
```

## Architecture

Single-process Streamlit app with no sidebar. Navigation is driven entirely by `st.session_state.page`.

```
app.py                      # Entry point: init_db(), 3-tab layout (Projects | Employees | Commission)
database.py                 # SQLAlchemy models + SQLite (commission.db) + init_db() seeding
calculator.py               # Pure functions — no DB imports. All commission math lives here.
utils.py                    # CSS injection, color constants, HTML component helpers
pages/
  settings.py               # Commission bracket editor (accessed via ☰ popover)
  employees.py              # Employee CRUD with inline editing
  project_detail.py         # Project header + Team tab + Collections tab
  employee_statement.py     # Per-employee commission statement + payments
```

## Data Model

**Project-centric**: Collections belong to Projects. Employees are linked to Projects via `ProjectAssignment` (with a `distribution` 0.0–1.0 percentage). Commission is computed per employee by aggregating all collections across their assigned projects.

Key relationships:
- `Project` → `Collection[]` (cascade delete)
- `Project` → `ProjectAssignment[]` → `Employee`
- `Employee` → `CommissionCycle` (threshold settings)
- `Employee` → `EmployeePayment[]`

`CommissionCycle.commission_threshold` property = `applicable_threshold − threshold_carryforward`.

## Commission Calculation Logic

Entry point: `calculator.compute_employee_statement(collections, brackets, commission_threshold, total_payments)`.

Each `CollectionInput` has a `distribution` field (employee's share %). `employee_net_revenue = net_revenue × distribution`.

**Tiered marginal brackets** (seeded from xlsx, editable in Settings):
- $0–$1M: 2%, $1M–$3M: 3%, $3M–$7M: 4%, above $7M: 5%

**Threshold rule**: no commission until cumulative employee net revenue exceeds `commission_threshold`. Once crossed, commission is earned retroactively on all revenue from $0 (catch-up computed in `_marginal_commission`).

## UI Patterns

- **Two-section visual pattern**: green box (`GREEN_LIGHT` bg + `GREEN` border) for action/input forms; white box (`BORDER_GRAY` border) for existing data lists.
- `st.session_state.editing_emp_id` / `editing_team_emp_id` / `editing_project` / `editing_cycle` track inline edit state.
- Color constants in `utils.py`: `GREEN="#16A34A"`, `GREEN_LIGHT="#DCFCE7"`, `GREEN_TEXT="#14532D"`.
- All custom HTML rendered via `st.markdown(..., unsafe_allow_html=True)`.

## Deployment

`render.yaml` is configured for Render.com (Python 3.11, SQLite — ephemeral on Render; migrate to PostgreSQL for production persistence).

## Verification

Enter sample ABC transactions and verify commission amounts:
- $50k net → $1,000 earned (2% × $50k)
- +$500k → $10,000 earned (running total $11,000)
- +$1M → $25,500 earned (running total $36,500)
- +$2.5M → $85,500 earned (running total $122,000)
