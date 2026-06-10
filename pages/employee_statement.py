"""
Per-employee commission statement across all assigned projects.
"""
import io
import datetime
from typing import Optional

import pandas as pd
import streamlit as st
from sqlalchemy import func

from database import (
    Collection, CommissionBracket, CommissionCycle,
    Employee, EmployeePayment, Project, ProjectAssignment, get_session,
)
from calculator import BracketRow, CollectionInput, compute_employee_statement


def _load_brackets(session) -> list[BracketRow]:
    rows = session.query(CommissionBracket).order_by(CommissionBracket.sort_order).all()
    return [BracketRow(upper_bound=b.upper_bound, rate=b.rate, sort_order=b.sort_order) for b in rows]


def render(employee_id: Optional[int] = None):
    with get_session() as session:
        employees = session.query(Employee).order_by(Employee.name).all()
        if not employees:
            st.warning("No employees found. Add employees via the ☰ menu.")
            return

        # Employee selector
        emp_names = [e.name for e in employees]
        emp_ids = [e.id for e in employees]
        default_idx = emp_ids.index(employee_id) if employee_id in emp_ids else 0

        selected_name = st.selectbox("Employee", emp_names, index=default_idx)
        emp = employees[emp_names.index(selected_name)]
        st.session_state["selected_employee_id"] = emp.id

        cycle = (
            session.query(CommissionCycle)
            .filter_by(employee_id=emp.id)
            .order_by(CommissionCycle.id)
            .first()
        )
        if cycle is None:
            st.error("No commission cycle found for this employee.")
            return

        brackets = _load_brackets(session)

        # ── Cycle / threshold info ────────────────────────────────────────────
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Start Date", str(emp.employment_date) if emp.employment_date else "—")
        col2.metric("Commission Threshold", f"${cycle.commission_threshold:,.0f}")

        with col4:
            if st.button("Edit Settings", key="edit_cycle_toggle"):
                st.session_state["editing_cycle"] = not st.session_state.get("editing_cycle", False)

        if st.session_state.get("editing_cycle"):
            with st.form("edit_cycle_form"):
                new_name = st.text_input("Name", value=emp.name)
                new_date = st.date_input("Employment Date", value=emp.employment_date or datetime.date.today())
                new_thresh = st.number_input("Commission Threshold ($)", min_value=0.0, value=float(cycle.applicable_threshold), step=1000.0)
                new_carry = st.number_input("Threshold Carryforward ($)", min_value=0.0, value=float(cycle.threshold_carryforward), step=1000.0)
                if st.form_submit_button("Save", type="primary"):
                    e = session.get(Employee, emp.id)
                    e.name = new_name.strip() or e.name
                    e.employment_date = new_date
                    c = session.get(CommissionCycle, cycle.id)
                    c.applicable_threshold = new_thresh
                    c.threshold_carryforward = new_carry
                    session.commit()
                    st.session_state["editing_cycle"] = False
                    st.rerun()

        st.divider()

        # ── Gather collections across all assigned projects ────────────────────
        query = (
            session.query(Collection, ProjectAssignment.distribution, Project.project_no, Project.customer)
            .join(Project, Collection.project_id == Project.id)
            .join(ProjectAssignment, ProjectAssignment.project_id == Project.id)
            .filter(ProjectAssignment.employee_id == emp.id)
        )
        if cycle.start_date:
            query = query.filter(Collection.collection_date >= cycle.start_date)
        if cycle.end_date:
            query = query.filter(Collection.collection_date <= cycle.end_date)
        raw = query.order_by(Collection.collection_date, Collection.id).all()

        collections = [
            CollectionInput(
                id=col.id,
                project_id=col.project_id,
                project_no=project_no,
                customer=customer,
                collection_amount=col.collection_amount,
                collection_date=col.collection_date,
                sales_tax=col.sales_tax,
                referral_fee=col.referral_fee,
                approved_sales_exp=col.approved_sales_exp,
                distribution=dist,
            )
            for col, dist, project_no, customer in raw
        ]

        # ── Payments ──────────────────────────────────────────────────────────
        payments = session.query(EmployeePayment).filter_by(employee_id=emp.id).order_by(EmployeePayment.payment_date).all()
        total_payments = sum(p.amount for p in payments)

        if not collections:
            st.info("No collections found for this employee. Assign them to a project and add collections.")
        else:
            rows = compute_employee_statement(collections, brackets, cycle.commission_threshold, total_payments)
            last = rows[-1]

            # Summary metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Net Revenue (Share)", f"${last.calc_revenue_accumulated:,.2f}")
            m2.metric("Total Commission Earned", f"${last.commission_accumulated:,.2f}")
            m3.metric("Total Paid Out", f"${total_payments:,.2f}")
            m4.metric("Balance Due", f"${last.commission_due:,.2f}")

            st.divider()

            records = [
                {
                    "Date": r.collection_date,
                    "Customer": r.customer or "—",
                    "Project": r.project_no or "—",
                    "Collected ($)": r.collection_amount,
                    "Net Revenue ($)": r.net_revenue,
                    "Share": f"{r.distribution*100:.0f}%",
                    "Employee Net ($)": r.employee_net_revenue,
                    "Accum. Revenue ($)": r.calc_revenue_accumulated,
                    "Commission Earned ($)": r.commission_earned,
                    "Accum. Earned ($)": r.commission_accumulated,
                    "Balance Due ($)": r.commission_due,
                }
                for r in rows
            ]
            df = pd.DataFrame(records)
            currency_cols = [c for c in df.columns if "($)" in c]
            st.dataframe(
                df.style.format({c: "${:,.2f}" for c in currency_cols}, na_rep="—"),
                use_container_width=True,
                hide_index=True,
            )

            # Excel export
            def build_excel() -> bytes:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="Statement", index=False)
                    pd.DataFrame([
                        {"Cumulative Revenue (USD)": f"${b.upper_bound:,.0f}" if b.upper_bound else "∞",
                         "Rate": f"{b.rate*100:.2f}%"}
                        for b in brackets
                    ]).to_excel(writer, sheet_name="Brackets", index=False)
                return buf.getvalue()

            st.download_button(
                "Export to Excel",
                data=build_excel(),
                file_name=f"Statement_{emp.name.replace(' ','_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        # ── Payments section ──────────────────────────────────────────────────
        st.divider()
        st.subheader("Payments")

        if payments:
            for p in payments:
                col1, col2, col3, col4 = st.columns([2, 2, 3, 1])
                col1.write(str(p.payment_date) if p.payment_date else "—")
                col2.write(f"${p.amount:,.2f}")
                col3.write(p.note or "")
                if col4.button("✕", key=f"del_pay_{p.id}", help="Delete"):
                    session.delete(session.get(EmployeePayment, p.id))
                    session.commit()
                    st.rerun()
        else:
            st.caption("No payments recorded.")

        with st.form("add_payment_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                amt = st.number_input("Amount ($)", min_value=0.0, value=0.0, step=100.0)
            with col2:
                pay_date = st.date_input("Date", value=datetime.date.today())
            with col3:
                note = st.text_input("Note", placeholder="e.g. advance, settlement")
            if st.form_submit_button("Add Payment", type="primary"):
                if amt > 0:
                    session.add(EmployeePayment(employee_id=emp.id, amount=amt, payment_date=pay_date, note=note or None))
                    session.commit()
                    st.rerun()
