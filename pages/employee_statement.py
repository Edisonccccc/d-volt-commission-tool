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
from utils import employee_avatar, badge, GREEN, GREEN_LIGHT, GREEN_TEXT, TEXT_LIGHT, TEXT_MID, TEXT_DARK, BORDER_GRAY


def _load_brackets(session) -> list[BracketRow]:
    return [
        BracketRow(upper_bound=b.upper_bound, rate=b.rate, sort_order=b.sort_order)
        for b in session.query(CommissionBracket).order_by(CommissionBracket.sort_order)
    ]


_CARD_H = 104  # px — card height (avatar 44 + padding 26 + gap 8 + name 20 + border 2 + slack 4)


def render(employee_id: Optional[int] = None):
    st.markdown(f"""
    <style>
    /* ── Employee picker ─────────────────────────────────────────────────── */
    /* Button is rendered FIRST (sets layout height), card is rendered SECOND
       and positioned absolute on top. Scoped via :has(.emp-card) on column. */
    [data-testid="column"]:has(.emp-card) > [data-testid="stVerticalBlock"] {{
        position: relative !important;
        height: {_CARD_H}px !important;
    }}
    /* First child = button wrapper: invisible but full-height and clickable */
    [data-testid="column"]:has(.emp-card) > [data-testid="stVerticalBlock"] > div:first-child button {{
        height: {_CARD_H}px !important;
        width: 100% !important;
        opacity: 0 !important;
        cursor: pointer !important;
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        display: block !important;
    }}
    /* Last child = card markdown wrapper: absolute overlay, no pointer events */
    [data-testid="column"]:has(.emp-card) > [data-testid="stVerticalBlock"] > div:last-child {{
        position: absolute !important;
        top: 0 !important; left: 0 !important; right: 0 !important;
        pointer-events: none !important;
        z-index: 5 !important;
    }}
    /* Hover: highlight card when cursor is over the invisible button */
    [data-testid="column"]:has(.emp-card):has(button:hover) .emp-card {{
        border-color: {GREEN} !important;
        background: {GREEN_LIGHT} !important;
        box-shadow: 0 3px 14px rgba(22,163,74,0.22) !important;
    }}
    [data-testid="column"]:has(.emp-card):has(button:hover) .emp-card-name {{
        color: {GREEN_TEXT} !important;
        font-weight: 700 !important;
    }}
    </style>
    """, unsafe_allow_html=True)

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

        emp_ids = [e.id for e in employees]
        selected_id = st.session_state.get("selected_employee_id")
        if selected_id not in emp_ids:
            selected_id = employees[0].id
        emp = next(e for e in employees if e.id == selected_id)

        # ── Employee picker ───────────────────────────────────────────────────
        st.markdown(
            f'<div style="font-size:0.68rem;font-weight:700;color:{TEXT_LIGHT};'
            f'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.6rem;">'
            f'Select Employee</div>',
            unsafe_allow_html=True,
        )

        cols = st.columns(len(employees))
        for i, e in enumerate(employees):
            with cols[i]:
                is_sel = e.id == selected_id
                border = f"2.5px solid {GREEN}" if is_sel else f"1.5px solid {BORDER_GRAY}"
                bg = GREEN_LIGHT if is_sel else "white"
                name_color = GREEN_TEXT if is_sel else TEXT_DARK
                name_weight = "700" if is_sel else "500"
                shadow = "0 2px 10px rgba(22,163,74,0.2)" if is_sel else "0 1px 3px rgba(0,0,0,0.06)"
                # Button FIRST — invisible, sets column height, receives clicks
                if st.button("", key=f"pick_emp_{e.id}", use_container_width=True):
                    st.session_state["selected_employee_id"] = e.id
                    st.rerun()
                # Card SECOND — CSS positions it absolute on top of the button
                st.markdown(
                    f'<div class="emp-card" style="background:{bg};border:{border};'
                    f'border-radius:14px;padding:14px 6px 12px 6px;text-align:center;'
                    f'box-shadow:{shadow};transition:all 0.15s ease;">'
                    f'{employee_avatar(e.name, size=44, gender=e.gender)}'
                    f'<div class="emp-card-name" style="font-size:0.78rem;font-weight:{name_weight};'
                    f'color:{name_color};margin-top:8px;overflow:hidden;text-overflow:ellipsis;'
                    f'white-space:nowrap;">{e.name.split()[0]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.divider()

        cycle = (
            session.query(CommissionCycle)
            .filter_by(employee_id=emp.id)
            .order_by(CommissionCycle.id)
            .first()
        )
        if not cycle:
            st.error("No commission cycle found for this employee.")
            return

        # ── Selected employee header ──────────────────────────────────────────
        av_col, info_col = st.columns([0.5, 7])
        av_col.markdown(employee_avatar(emp.name, size=52, gender=emp.gender), unsafe_allow_html=True)
        info_col.markdown(f"### {emp.name}")
        info_col.markdown(
            badge(f"Started {emp.employment_date}" if emp.employment_date else "No start date", "gray") +
            "&nbsp;&nbsp;" + badge(f"Threshold: ${cycle.commission_threshold:,.0f}", "blue"),
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:0.25rem;'></div>", unsafe_allow_html=True)

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
            st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:white;border:1px solid {BORDER_GRAY};border-radius:12px;
                padding:2.5rem;text-align:center;color:{TEXT_LIGHT};">
                <div style="font-size:1.5rem;margin-bottom:8px;">📭</div>
                <div style="font-size:0.9rem;font-weight:600;color:#64748B;">No collections yet</div>
                <div style="font-size:0.8rem;margin-top:4px;">Assign this employee to a project and add collections.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            rows = compute_employee_statement(collections, brackets, cycle.commission_threshold, total_payments)
            last = rows[-1]
            balance = last.commission_due

            # ── Summary — highlighted green card ─────────────────────────────
            st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#F0FDF4;border:1.5px solid #BBF7D0;border-left:5px solid {GREEN};
                border-radius:12px;padding:1.25rem 1.5rem 0.6rem 1.4rem;
                box-shadow:0 2px 8px rgba(22,163,74,0.1);">
                <div style="font-size:0.75rem;font-weight:800;color:{GREEN_TEXT};
                    text-transform:uppercase;letter-spacing:0.1em;margin-bottom:1rem;">
                    Commission Summary
                </div>
            """, unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Net Revenue (Share)", f"${last.calc_revenue_accumulated:,.0f}")
            m2.metric("Commission Earned", f"${last.commission_accumulated:,.0f}")
            m3.metric("Paid Out", f"${total_payments:,.0f}")
            m4.metric("Balance Due", f"${balance:,.0f}")

            if balance > 0:
                st.markdown(
                    f'<div style="background:#FEF9C3;border:1px solid #FDE047;border-radius:8px;'
                    f'padding:9px 14px;margin:10px 0 4px 0;">'
                    f'<b style="color:#713F12;">⚠ &nbsp;${balance:,.2f} commission outstanding</b></div>',
                    unsafe_allow_html=True,
                )
            elif balance < 0:
                st.markdown(
                    f'<div style="background:#DCFCE7;border:1px solid #86EFAC;border-radius:8px;'
                    f'padding:9px 14px;margin:10px 0 4px 0;">'
                    f'<b style="color:#14532D;">✓ &nbsp;Fully paid — overpaid by ${abs(balance):,.2f}</b></div>',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

            # ── Statement Detail ──────────────────────────────────────────────
            st.markdown("<div style='height:1.25rem;'></div>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.6rem;">
                <div style="font-size:0.8rem;font-weight:700;color:{TEXT_DARK};">
                    📋 &nbsp;Statement Detail
                </div>
                <span style="background:#F3F4F6;color:{TEXT_MID};padding:2px 10px;
                    border-radius:20px;font-size:0.72rem;font-weight:600;">{len(rows)} rows</span>
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

            _, dl_col = st.columns([3, 1])
            with dl_col:
                st.download_button(
                    "⬇ Export Excel",
                    data=build_excel(),
                    file_name=f"Statement_{emp.name.replace(' ','_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

        # ── Record Payment ────────────────────────────────────────────────────
        st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.6rem;">
            <div style="font-size:0.8rem;font-weight:700;color:{TEXT_DARK};">
                ➕ &nbsp;Record Payment
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
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

        # ── Payment History ───────────────────────────────────────────────────
        st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

        total_html = (
            f'<span style="background:#F3F4F6;color:{TEXT_MID};padding:2px 10px;'
            f'border-radius:20px;font-size:0.72rem;font-weight:600;">{len(payments)}</span>'
            f'&nbsp;&nbsp;<span style="color:{TEXT_MID};font-size:0.78rem;">'
            f'Total paid: <b style="color:{TEXT_DARK};">${total_payments:,.2f}</b></span>'
        ) if payments else (
            f'<span style="background:#F3F4F6;color:{TEXT_MID};padding:2px 10px;'
            f'border-radius:20px;font-size:0.72rem;font-weight:600;">0</span>'
        )

        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.6rem;">
            <div style="font-size:0.8rem;font-weight:700;color:{TEXT_DARK};">
                💳 &nbsp;Payment History
            </div>
            {total_html}
        </div>
        """, unsafe_allow_html=True)

        if payments:
            with st.container(border=True):
                for idx, p in enumerate(payments):
                    row_left, row_right = st.columns([9, 1])
                    with row_left:
                        note_html = (
                            f'<span style="background:#F1F5F9;color:{TEXT_MID};'
                            f'padding:2px 9px;border-radius:20px;font-size:0.74rem;">{p.note}</span>'
                            if p.note else ""
                        )
                        sep = "border-bottom:1px solid #F1F5F9;" if idx < len(payments) - 1 else ""
                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:14px;'
                            f'padding:10px 2px;{sep}">'
                            f'<span style="color:{TEXT_MID};font-size:0.82rem;min-width:96px;">'
                            f'{p.payment_date or "—"}</span>'
                            f'<span style="font-weight:700;color:{TEXT_DARK};font-size:1rem;">'
                            f'${p.amount:,.2f}</span>'
                            f'{note_html}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    with row_right:
                        if st.button("✕", key=f"del_pay_{p.id}", help="Remove payment"):
                            session.delete(session.get(EmployeePayment, p.id))
                            session.commit()
                            st.rerun()
        else:
            st.markdown(
                f'<div style="color:{TEXT_LIGHT};font-size:0.875rem;padding:0.5rem 0;">'
                f'No payments recorded yet.</div>',
                unsafe_allow_html=True,
            )
