import io
import datetime

import pandas as pd
import streamlit as st

from database import CommissionBracket, CommissionCycle, Employee, Transaction, get_session
from calculator import BracketRow, TxnInput, compute_statement


def _cycle_label(cycle: CommissionCycle) -> str:
    return (
        f"{cycle.employee.name} | "
        f"{cycle.start_date or '?'} → {cycle.end_date or '?'}"
    )


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


def render():
    st.header("Commission Statement")

    with get_session() as session:
        cycles = (
            session.query(CommissionCycle)
            .join(Employee)
            .order_by(Employee.name, CommissionCycle.start_date.desc())
            .all()
        )

        if not cycles:
            st.warning("No commission cycles found.")
            return

        labels = [_cycle_label(c) for c in cycles]
        selected_label = st.selectbox("Select Cycle", labels)
        cycle = cycles[labels.index(selected_label)]

        brackets_db = session.query(CommissionBracket).order_by(CommissionBracket.sort_order).all()
        brackets = [BracketRow(upper_bound=b.upper_bound, rate=b.rate, sort_order=b.sort_order) for b in brackets_db]

        txns = (
            session.query(Transaction)
            .filter_by(cycle_id=cycle.id)
            .order_by(Transaction.collection_date, Transaction.id)
            .all()
        )

        # Summary header
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Employee", cycle.employee.name)
        col2.metric(
            "Cycle",
            f"{cycle.start_date or '?'} → {cycle.end_date or '?'}",
        )
        col3.metric("Commission Threshold", f"${cycle.commission_threshold:,.0f}")
        col4.metric("Transactions", len(txns))

        st.divider()

        if not txns:
            st.info("No transactions in this cycle.")
            return

        rows = compute_statement(
            [_to_txn_input(t) for t in txns],
            brackets,
            cycle.commission_threshold,
        )

        # Build display dataframe
        records = []
        for r in rows:
            records.append({
                "Customer": r.customer or "",
                "Project No.": r.project_no or "",
                "Product": r.product_description or "",
                "Qty": r.qty,
                "Contract ($)": r.contract_amount,
                "Collection ($)": r.collection_amount,
                "Collection Date": r.collection_date,
                "Sales Tax ($)": r.net_revenue - r.collection_amount + (
                    # back-calculate: net = col - tax - ref - exp
                    0  # shown separately below
                ),
                "Net Revenue ($)": r.net_revenue,
                "Comm. Weight": r.commission_weight,
                "Calc Rev Base ($)": r.calc_revenue_base,
                "Calc Rev Accum. ($)": r.calc_revenue_accumulated,
                "Commission Earned ($)": r.commission_earned,
                "Commission Accum. ($)": r.commission_accumulated,
                "Commission Payable ($)": r.commission_payable,
                "Settlement ($)": r.settlement_amount,
                "Settlement Date": r.settlement_date,
                "Advance Paid ($)": r.advance_paid,
                "Advance Date": r.advance_date,
                "Commission Due ($)": r.commission_due,
                "Exp Allowance ($)": r.exp_allowance,
                "Bal Due/Owed ($)": r.bal_due_owed,
            })

        df = pd.DataFrame(records)

        # Summary totals row
        last = rows[-1]
        st.subheader("Totals")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Net Revenue", f"${last.calc_revenue_accumulated:,.2f}")
        m2.metric("Total Commission Earned", f"${last.commission_accumulated:,.2f}")
        m3.metric("Total Settlements + Advances", f"${sum(r.settlement_amount + r.advance_paid for r in rows):,.2f}")
        m4.metric("Balance Due/Owed", f"${last.bal_due_owed:,.2f}")

        st.divider()
        st.subheader("Detailed Statement")

        # Format currency columns
        currency_cols = [c for c in df.columns if "($)" in c]
        fmt = {c: "${:,.2f}" for c in currency_cols}

        st.dataframe(
            df.style.format(fmt, na_rep="—"),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        # Export to Excel
        def build_excel() -> bytes:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="CommStatement", index=False)

                # Brackets sheet
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

        fname = (
            f"CommStatement_{cycle.employee.name.replace(' ','_')}"
            f"_{cycle.start_date or 'unknown'}.xlsx"
        )
        st.download_button(
            label="Export to Excel",
            data=build_excel(),
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
