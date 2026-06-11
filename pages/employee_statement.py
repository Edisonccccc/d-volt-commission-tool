"""Per-employee commission statement across all assigned projects."""
import io
import datetime
from typing import Optional

import pandas as pd
import streamlit as st

from database import (
    Collection, CommissionBracket, CommissionCycle,
    Employee, EmployeePayment, Project, ProjectAssignment, get_session,
)
from calculator import BracketRow, CollectionInput, compute_employee_statement
from utils import avatar, employee_avatar, badge, section_title, GREEN, GREEN_LIGHT, GREEN_TEXT, TEXT_LIGHT, TEXT_MID


def _load_brackets(session) -> list[BracketRow]:
    return [
        BracketRow(upper_bound=b.upper_bound, rate=b.rate, sort_order=b.sort_order)
        for b in session.query(CommissionBracket).order_by(CommissionBracket.sort_order)
    ]


def render(employee_id: Optional[int] = None):
    with get_session() as session:
        employees = session.query(Employee).order_by(Employee.name).all()
        if not employees:
            st.markdown("""
            <div style="text-align:center;padding:3rem 1rem;color:#94A3B8;">
                <div style="font-size:2.5rem;margin-bottom:12px;">💰</div>
                <div style="font-size:1rem;font-weight:600;color:#64748B;">No employees yet</div>
                <div style="font-size:0.85rem;margin-top:4px;">Add employees in the Employees tab first.</div>
            </div>
            """, unsafe_allow_html=True)
            return

        emp_names = [e.name for e in employees]
        emp_ids = [e.id for e in employees]
        default_idx = emp_ids.index(employee_id) if employee_id in emp_ids else 0

        # Employee selector row
        sel_col, edit_col = st.columns([5, 1])
        with sel_col:
            selected_name = st.selectbox("Select Employee", emp_names, index=default_idx, label_visibility="collapsed")
        emp = employees[emp_names.index(selected_name)]
        st.session_state["selected_employee_id"] = emp.id

        cycle = (
            session.query(CommissionCycle)
            .filter_by(employee_id=emp.id)
            .order_by(CommissionCycle.id)
            .first()
        )
        if not cycle:
            st.error("No commission cycle found for this employee.")
            return

        # Employee info bar
        av_col, info_col, edit_col = st.columns([0.4, 6, 1])
        av_col.markdown(employee_avatar(emp.name, size=48, gender=emp.gender), unsafe_allow_html=True)
        info_col.markdown(f"### {emp.name}")
        info_col.markdown(
            badge(f"Started {emp.employment_date}" if emp.employment_date else "No start date", "gray") +
            "  " + badge(f"Threshold: ${cycle.commission_threshold:,.0f}", "blue"),
            unsafe_allow_html=True,
        )
        with edit_col:
            st.markdown("<div style='padding-top:12px;'>", unsafe_allow_html=True)
            if st.button("Edit", key="edit_cycle_toggle"):
                st.session_state["editing_cycle"] = not st.session_state.get("editing_cycle", False)
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.get("editing_cycle"):
            with st.form("edit_cycle_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_name = st.text_input("Name", value=emp.name)
                    new_date = st.date_input("Employment Date", value=emp.employment_date or datetime.date.today())
                with col2:
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

        # Gather collections
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
                id=col.id, project_id=col.project_id, project_no=pno, customer=cust,
                collection_amount=col.collection_amount, collection_date=col.collection_date,
                sales_tax=col.sales_tax, referral_fee=col.referral_fee,
                approved_sales_exp=col.approved_sales_exp, distribution=dist,
            )
            for col, dist, pno, cust in raw
        ]

        payments = session.query(EmployeePayment).filter_by(employee_id=emp.id).order_by(EmployeePayment.payment_date).all()
        total_payments = sum(p.amount for p in payments)
        brackets = _load_brackets(session)

        if not collections:
            st.markdown(f"""
            <div style="background:white;border:1px solid #E5E7EB;border-radius:12px;
                padding:2rem;text-align:center;color:{TEXT_LIGHT};margin-bottom:1.5rem;">
                No collections yet — assign this employee to a project and add collections.
            </div>
            """, unsafe_allow_html=True)
        else:
            rows = compute_employee_statement(collections, brackets, cycle.commission_threshold, total_payments)
            last = rows[-1]
            balance = last.commission_due

            # ── Summary card ──────────────────────────────────────────────────
            st.markdown(f"""
            <div style="background:white;border:1px solid #E5E7EB;border-radius:14px;
                padding:1.25rem 1.5rem 0.75rem 1.5rem;margin-bottom:1.25rem;
                box-shadow:0 1px 4px rgba(0,0,0,0.05);">
                <div style="font-size:0.7rem;font-weight:700;color:{TEXT_LIGHT};
                    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:1rem;">
                    📊 &nbsp; Summary
                </div>
            """, unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Net Revenue (Share)", f"${last.calc_revenue_accumulated:,.0f}")
            m2.metric("Commission Earned", f"${last.commission_accumulated:,.0f}")
            m3.metric("Paid Out", f"${total_payments:,.0f}")
            m4.metric("Balance Due", f"${balance:,.0f}")

            if balance > 0:
                st.markdown(
                    f'<div style="background:#FEF9C3;border:1px solid #FDE047;border-radius:10px;'
                    f'padding:10px 16px;margin:10px 0 4px 0;">'
                    f'<b style="color:#713F12;">⚠ ${balance:,.2f} commission outstanding</b></div>',
                    unsafe_allow_html=True,
                )
            elif balance < 0:
                st.markdown(
                    f'<div style="background:{GREEN_LIGHT};border:1px solid #86EFAC;border-radius:10px;'
                    f'padding:10px 16px;margin:10px 0 4px 0;">'
                    f'<b style="color:#14532D;">✓ Overpaid by ${abs(balance):,.2f}</b></div>',
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)

            # ── Statement detail card ─────────────────────────────────────────
            st.markdown(f"""
            <div style="background:white;border:1px solid #E5E7EB;border-radius:14px;
                padding:1.25rem 1.5rem 1rem 1.5rem;margin-bottom:1.25rem;
                box-shadow:0 1px 4px rgba(0,0,0,0.05);">
                <div style="font-size:0.7rem;font-weight:700;color:{TEXT_LIGHT};
                    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:1rem;">
                    📋 &nbsp; Statement Detail
                </div>
            """, unsafe_allow_html=True)

            records = [
                {
                    "Date": r.collection_date,
                    "Customer": r.customer or "—",
                    "Project": r.project_no or "—",
                    "Collected ($)": r.collection_amount,
                    "Net Revenue ($)": r.net_revenue,
                    "Share %": f"{r.distribution*100:.0f}%",
                    "Employee Net ($)": r.employee_net_revenue,
                    "Accum. Revenue ($)": r.calc_revenue_accumulated,
                    "Comm. Earned ($)": r.commission_earned,
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

            def build_excel() -> bytes:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="Statement", index=False)
                    pd.DataFrame([
                        {"Revenue Range": f"${b.upper_bound:,.0f}" if b.upper_bound else "∞",
                         "Rate": f"{b.rate*100:.2f}%"}
                        for b in brackets
                    ]).to_excel(writer, sheet_name="Brackets", index=False)
                return buf.getvalue()

            st.download_button(
                "⬇  Export to Excel",
                data=build_excel(),
                file_name=f"Statement_{emp.name.replace(' ','_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            st.markdown("</div>", unsafe_allow_html=True)

        # ── Record Payment — green action zone ────────────────────────────────
        st.markdown(f"""
        <div style="background:{GREEN_LIGHT};border:2px solid {GREEN};border-radius:14px;
            padding:1.1rem 1.4rem 0.4rem 1.4rem;margin-bottom:1.25rem;">
            <div style="font-size:0.72rem;font-weight:800;color:{GREEN_TEXT};
                text-transform:uppercase;letter-spacing:0.1em;margin-bottom:1rem;">
                ➕ &nbsp; Record Payment
            </div>
        """, unsafe_allow_html=True)

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
                    session.add(EmployeePayment(
                        employee_id=emp.id, amount=amt,
                        payment_date=pay_date, note=note or None,
                    ))
                    session.commit()
                    st.rerun()
                else:
                    st.error("Amount must be greater than 0.")

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Payment history — white card ──────────────────────────────────────
        st.markdown(f"""
        <div style="background:white;border:1px solid #E5E7EB;border-radius:14px;
            padding:1.1rem 1.4rem 0.75rem 1.4rem;
            box-shadow:0 1px 4px rgba(0,0,0,0.05);">
            <div style="font-size:0.7rem;font-weight:700;color:{TEXT_LIGHT};
                text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.75rem;">
                💳 &nbsp; Payment History &nbsp;
                <span style="background:#F3F4F6;color:{TEXT_MID};padding:1px 8px;
                    border-radius:20px;font-size:0.7rem;">{len(payments)}</span>
            </div>
        """, unsafe_allow_html=True)

        if payments:
            for p in payments:
                row_left, row_right = st.columns([8, 1])
                with row_left:
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #F1F5F9;">'
                        f'<span style="color:#64748B;font-size:0.85rem;min-width:90px;">{p.payment_date or "—"}</span>'
                        f'<span style="font-weight:700;color:#1E293B;">${p.amount:,.2f}</span>'
                        f'{"<span style=color:#94A3B8;font-size:0.85rem;>" + p.note + "</span>" if p.note else ""}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with row_right:
                    if st.button("✕", key=f"del_pay_{p.id}", help="Remove"):
                        session.delete(session.get(EmployeePayment, p.id))
                        session.commit()
                        st.rerun()
        else:
            st.markdown(f'<div style="color:{TEXT_LIGHT};font-size:0.875rem;padding:0.5rem 0 0.75rem;">No payments recorded yet.</div>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
