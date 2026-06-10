"""
Single-page view for a selected employee.
Shows: employee info, then two tabs — Transactions (add/edit) and Statement (computed).
"""
import datetime
import io

import pandas as pd
import streamlit as st

from database import (
    CommissionBracket,
    CommissionCycle,
    Employee,
    Transaction,
    get_session,
)
from calculator import BracketRow, TxnInput, StatementRow, compute_statement


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_brackets(session) -> list[BracketRow]:
    rows = session.query(CommissionBracket).order_by(CommissionBracket.sort_order).all()
    return [BracketRow(upper_bound=b.upper_bound, rate=b.rate, sort_order=b.sort_order) for b in rows]


def _to_txn_input(t: Transaction) -> TxnInput:
    return TxnInput(
        id=t.id,
        customer=t.customer,
        project_no=t.project_no,
        product_description=t.product_description,
        qty=t.qty,
        contract_amount=t.contract_amount,
        collection_amount=t.collection_amount,
        collection_date=t.collection_date,
        sales_tax=t.sales_tax,
        referral_fee=t.referral_fee,
        approved_sales_exp=t.approved_sales_exp,
        commission_weight=t.commission_weight,
        settlement_amount=t.settlement_amount,
        settlement_date=t.settlement_date,
        advance_paid=t.advance_paid,
        advance_date=t.advance_date,
    )


def _fmt(val, prefix="$"):
    if val is None:
        return "—"
    return f"{prefix}{val:,.2f}"


# ── Employee header ───────────────────────────────────────────────────────────

def _render_employee_header(session, emp: Employee, cycle: CommissionCycle):
    col_name, col_date, col_thresh, col_edit = st.columns([3, 2, 2, 1])
    col_name.metric("Employee", emp.name)
    col_date.metric("Start Date", str(emp.employment_date) if emp.employment_date else "—")
    col_thresh.metric("Commission Threshold", f"${cycle.commission_threshold:,.0f}")

    with col_edit:
        if st.button("Edit", key="edit_emp_toggle"):
            st.session_state["editing_employee"] = not st.session_state.get("editing_employee", False)

    if st.session_state.get("editing_employee"):
        with st.form("edit_employee_form"):
            st.subheader("Edit Employee")
            new_name = st.text_input("Full Name", value=emp.name)
            new_date = st.date_input(
                "Date of Employment",
                value=emp.employment_date,
                min_value=datetime.date(2000, 1, 1),
            )
            new_thresh = st.number_input(
                "Commission Threshold ($)",
                min_value=0.0,
                value=float(cycle.applicable_threshold),
                step=1000.0,
            )
            new_carryforward = st.number_input(
                "Threshold Carryforward ($)",
                min_value=0.0,
                value=float(cycle.threshold_carryforward),
                step=1000.0,
                help="Revenue already counted from a previous period — reduces the effective threshold.",
            )
            if st.form_submit_button("Save", type="primary"):
                if not new_name.strip():
                    st.error("Name is required.")
                else:
                    e = session.get(Employee, emp.id)
                    e.name = new_name.strip()
                    e.employment_date = new_date
                    c = session.get(CommissionCycle, cycle.id)
                    c.applicable_threshold = new_thresh
                    c.threshold_carryforward = new_carryforward
                    session.commit()
                    st.session_state["editing_employee"] = False
                    st.rerun()


# ── Transactions tab ──────────────────────────────────────────────────────────

def _render_transactions(session, cycle: CommissionCycle):
    txns = (
        session.query(Transaction)
        .filter_by(cycle_id=cycle.id)
        .order_by(Transaction.collection_date, Transaction.id)
        .all()
    )

    # Add transaction form
    with st.expander("➕ Add Transaction", expanded=not txns):
        with st.form("add_txn_form"):
            col1, col2 = st.columns(2)
            with col1:
                customer = st.text_input("Customer Name")
                project_no = st.text_input("Project / PO Number")
                collection_date = st.date_input("Collection Date", value=datetime.date.today())
                contract_amount = st.number_input("Contract / PO Amount ($)", min_value=0.0, value=0.0, step=1000.0)
            with col2:
                collection_amount = st.number_input("Amount Collected ($)", min_value=0.0, value=0.0, step=1000.0)
                sales_tax = st.number_input("Sales Tax ($)", min_value=0.0, value=0.0, step=100.0)
                referral_fee = st.number_input("Referral Fee ($)", min_value=0.0, value=0.0, step=100.0)
                approved_exp = st.number_input("Approved Sales Expenses ($)", min_value=0.0, value=0.0, step=100.0)

            with st.expander("Settlement / Advance (optional)"):
                col3, col4 = st.columns(2)
                with col3:
                    settlement_amount = st.number_input("Settlement Amount ($)", value=0.0, step=100.0)
                    settlement_date = st.date_input("Settlement Date", value=None, key="add_sdate")
                with col4:
                    advance_paid = st.number_input("Advance Paid ($)", value=0.0, step=100.0)
                    advance_date = st.date_input("Advance Date", value=None, key="add_adate")

            if st.form_submit_button("Add Transaction", type="primary"):
                session.add(Transaction(
                    cycle_id=cycle.id,
                    customer=customer or None,
                    project_no=project_no or None,
                    collection_amount=collection_amount,
                    collection_date=collection_date,
                    contract_amount=contract_amount,
                    sales_tax=sales_tax,
                    referral_fee=referral_fee,
                    approved_sales_exp=approved_exp,
                    commission_weight=1.0,
                    settlement_amount=settlement_amount,
                    settlement_date=settlement_date,
                    advance_paid=advance_paid,
                    advance_date=advance_date,
                ))
                session.commit()
                st.success("Transaction added.")
                st.rerun()

    if not txns:
        st.info("No transactions yet. Add one above.")
        return

    st.markdown(f"**{len(txns)} transaction(s)**")
    for txn in txns:
        net = txn.collection_amount - txn.sales_tax - txn.referral_fee - txn.approved_sales_exp
        label = (
            f"{txn.collection_date or '?'}  ·  "
            f"{txn.customer or '—'}  ·  "
            f"Collected: {_fmt(txn.collection_amount)}  ·  "
            f"Net: {_fmt(net)}"
        )
        with st.expander(label):
            with st.form(f"edit_txn_{txn.id}"):
                col1, col2 = st.columns(2)
                with col1:
                    nc = st.text_input("Customer Name", value=txn.customer or "", key=f"c_{txn.id}")
                    np = st.text_input("Project / PO Number", value=txn.project_no or "", key=f"p_{txn.id}")
                    ncd = st.date_input("Collection Date", value=txn.collection_date, key=f"cd_{txn.id}")
                    nca = st.number_input("Contract / PO Amount ($)", min_value=0.0, value=float(txn.contract_amount or 0), step=1000.0, key=f"ca_{txn.id}")
                with col2:
                    ncol = st.number_input("Amount Collected ($)", min_value=0.0, value=float(txn.collection_amount), step=1000.0, key=f"col_{txn.id}")
                    ntax = st.number_input("Sales Tax ($)", min_value=0.0, value=float(txn.sales_tax), step=100.0, key=f"tx_{txn.id}")
                    nref = st.number_input("Referral Fee ($)", min_value=0.0, value=float(txn.referral_fee), step=100.0, key=f"rf_{txn.id}")
                    nexp = st.number_input("Approved Sales Expenses ($)", min_value=0.0, value=float(txn.approved_sales_exp), step=100.0, key=f"ae_{txn.id}")

                with st.expander("Settlement / Advance"):
                    col3, col4 = st.columns(2)
                    with col3:
                        nsa = st.number_input("Settlement Amount ($)", value=float(txn.settlement_amount), step=100.0, key=f"sa_{txn.id}")
                        nsd = st.date_input("Settlement Date", value=txn.settlement_date, key=f"sd_{txn.id}")
                    with col4:
                        nap = st.number_input("Advance Paid ($)", value=float(txn.advance_paid), step=100.0, key=f"ap_{txn.id}")
                        nad = st.date_input("Advance Date", value=txn.advance_date, key=f"ad_{txn.id}")

                col_save, col_del = st.columns([4, 1])
                with col_save:
                    if st.form_submit_button("Save Changes", type="primary"):
                        t = session.get(Transaction, txn.id)
                        t.customer = nc or None
                        t.project_no = np or None
                        t.collection_date = ncd
                        t.contract_amount = nca
                        t.collection_amount = ncol
                        t.sales_tax = ntax
                        t.referral_fee = nref
                        t.approved_sales_exp = nexp
                        t.settlement_amount = nsa
                        t.settlement_date = nsd
                        t.advance_paid = nap
                        t.advance_date = nad
                        session.commit()
                        st.success("Saved.")
                        st.rerun()

            if st.button("Delete Transaction", key=f"del_{txn.id}", type="secondary"):
                session.delete(session.get(Transaction, txn.id))
                session.commit()
                st.rerun()


# ── Statement tab ─────────────────────────────────────────────────────────────

def _render_statement(session, emp: Employee, cycle: CommissionCycle):
    brackets = _load_brackets(session)
    txns = (
        session.query(Transaction)
        .filter_by(cycle_id=cycle.id)
        .order_by(Transaction.collection_date, Transaction.id)
        .all()
    )

    if not txns:
        st.info("No transactions yet — add some in the Transactions tab.")
        return

    rows = compute_statement(
        [_to_txn_input(t) for t in txns],
        brackets,
        cycle.commission_threshold,
    )
    last = rows[-1]

    # Summary metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Net Revenue", f"${last.calc_revenue_accumulated:,.2f}")
    m2.metric("Total Commission Earned", f"${last.commission_accumulated:,.2f}")
    total_paid = sum(r.settlement_amount + r.advance_paid for r in rows)
    m3.metric("Total Paid Out", f"${total_paid:,.2f}")
    m4.metric("Balance Due", f"${last.bal_due_owed:,.2f}")

    st.divider()

    records = [
        {
            "Date": r.collection_date,
            "Customer": r.customer or "—",
            "Project": r.project_no or "—",
            "Collected ($)": r.collection_amount,
            "Net Revenue ($)": r.net_revenue,
            "Accum. Revenue ($)": r.calc_revenue_accumulated,
            "Commission Earned ($)": r.commission_earned,
            "Accum. Earned ($)": r.commission_accumulated,
            "Settlement ($)": r.settlement_amount,
            "Advance ($)": r.advance_paid,
            "Balance Due ($)": r.bal_due_owed,
        }
        for r in rows
    ]
    df = pd.DataFrame(records)

    currency_cols = [c for c in df.columns if "($)" in c]
    fmt = {c: "${:,.2f}" for c in currency_cols}
    st.dataframe(df.style.format(fmt, na_rep="—"), use_container_width=True, hide_index=True)

    # Excel export
    def build_excel() -> bytes:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="CommStatement", index=False)
            prev = 0
            bracket_rows = []
            for b in brackets:
                lo = f"${prev:,.0f}"
                hi = f"${b.upper_bound:,.0f}" if b.upper_bound else "∞"
                bracket_rows.append({
                    "Cumulative Revenue (USD)": f"{lo} – {hi}",
                    "Marginal Commission Rate": f"{b.rate*100:.2f}%",
                })
                prev = b.upper_bound or prev
            pd.DataFrame(bracket_rows).to_excel(writer, sheet_name="CommBracket", index=False)
        return buf.getvalue()

    fname = f"CommStatement_{emp.name.replace(' ', '_')}.xlsx"
    st.download_button(
        "Export to Excel",
        data=build_excel(),
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── Main render ───────────────────────────────────────────────────────────────

def render(employee_id: int):
    with get_session() as session:
        emp = session.get(Employee, employee_id)
        if emp is None:
            st.error("Employee not found.")
            st.session_state.selected_employee_id = None
            return

        cycle = (
            session.query(CommissionCycle)
            .filter_by(employee_id=employee_id)
            .order_by(CommissionCycle.id)
            .first()
        )
        if cycle is None:
            # Shouldn't happen, but guard anyway
            st.error("No commission period found for this employee.")
            return

        _render_employee_header(session, emp, cycle)
        st.divider()

        tab_txn, tab_stmt = st.tabs(["Transactions", "Commission Statement"])
        with tab_txn:
            _render_transactions(session, cycle)
        with tab_stmt:
            _render_statement(session, emp, cycle)
