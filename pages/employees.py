"""Employees tab — manage employees and their commission settings."""
import datetime
from typing import Optional

import streamlit as st

from database import Employee, CommissionCycle, ProjectAssignment, EmployeePayment, get_session
from utils import employee_avatar, GREEN, GREEN_LIGHT, GREEN_TEXT, TEXT_MID, TEXT_LIGHT, TEXT_DARK, BORDER_GRAY


def render():
    st.markdown("""
    <style>
    div[data-testid="stExpander"] {
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    div[data-testid="stExpander"]:hover {
        border-color: #16A34A !important;
        box-shadow: 0 2px 10px rgba(22,163,74,0.12) !important;
    }
    div[data-testid="stExpander"] > details > summary:hover {
        background: #F0FDF4 !important;
    }
    div[data-testid="stExpander"] > details > summary {
        padding: 0.65rem 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with get_session() as session:
        employees = session.query(Employee).order_by(Employee.name).all()

        # ── Header bar ────────────────────────────────────────────────────────
        hdr_left, hdr_right = st.columns([6, 1])
        with hdr_left:
            st.markdown(f"""
            <div style="font-size:0.72rem;font-weight:800;color:{TEXT_LIGHT};
                text-transform:uppercase;letter-spacing:0.1em;padding-top:6px;">
                👥 &nbsp; Team Members &nbsp;
                <span style="background:#F3F4F6;color:{TEXT_MID};padding:1px 8px;
                    border-radius:20px;font-size:0.7rem;">{len(employees)}</span>
            </div>
            """, unsafe_allow_html=True)
        with hdr_right:
            showing = st.session_state.get("show_new_employee", False)
            if st.button("✕ Cancel" if showing else "➕ New",
                         type="secondary" if showing else "primary",
                         use_container_width=True, key="toggle_new_employee"):
                st.session_state.show_new_employee = not showing
                st.rerun()

        # ── Collapsible add form ──────────────────────────────────────────────
        if st.session_state.get("show_new_employee"):
            with st.container(border=True):
                with st.form("add_employee_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        name = st.text_input("Full Name")
                        emp_date = st.date_input("Start Date", value=datetime.date.today())
                        gender = st.selectbox("Gender *", ["— select —", "Male", "Female", "Other"], index=0)
                    with col2:
                        threshold = st.number_input(
                            "Commission Threshold ($)", min_value=0.0, value=20000.0, step=1000.0,
                            help="Minimum revenue before any commission is paid out.",
                        )
                        carryforward = st.number_input(
                            "Threshold Carryforward ($)", min_value=0.0, value=0.0, step=1000.0,
                            help="Revenue carried forward from a prior period.",
                        )
                    if st.form_submit_button("Add Employee", type="primary"):
                        if not name.strip():
                            st.error("Name is required.")
                        elif gender == "— select —":
                            st.error("Please select a gender.")
                        else:
                            emp = Employee(name=name.strip(), employment_date=emp_date,
                                           gender=gender.lower())
                            session.add(emp)
                            session.flush()
                            session.add(CommissionCycle(
                                employee_id=emp.id,
                                start_date=emp_date,
                                end_date=None,
                                applicable_threshold=threshold,
                                threshold_carryforward=carryforward,
                            ))
                            session.commit()
                            st.session_state.show_new_employee = False
                            st.rerun()
            st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)

        # ── Employee list ─────────────────────────────────────────────────────
        if not employees:
            st.markdown(f"""
            <div style="text-align:center;padding:3rem 1rem;color:{TEXT_LIGHT};
                background:white;border:1px solid {BORDER_GRAY};border-radius:12px;margin-top:1rem;">
                <div style="font-size:2.5rem;margin-bottom:12px;">👥</div>
                <div style="font-size:1rem;font-weight:600;color:#6B7280;">No employees yet</div>
                <div style="font-size:0.85rem;margin-top:4px;">Click <b>➕ New</b> above to add your first employee.</div>
            </div>
            """, unsafe_allow_html=True)
            return

        editing_id = st.session_state.get("editing_emp_id")

        for emp in employees:
            cycle = session.query(CommissionCycle).filter_by(employee_id=emp.id).first()
            proj_count = session.query(ProjectAssignment).filter_by(employee_id=emp.id).count()
            thresh = cycle.commission_threshold if cycle else 20000.0
            is_editing = editing_id == emp.id

            label = (f"**{emp.name}**  ·  "
                     f"Started {emp.employment_date or '—'}  ·  "
                     f"Threshold ${thresh:,.0f}  ·  "
                     f"{proj_count} project{'s' if proj_count != 1 else ''}")

            # Avatar always visible beside the expander
            av_col, exp_col = st.columns([0.42, 9])
            with av_col:
                st.markdown(
                    f'<div style="padding-top:8px;">'
                    f'{employee_avatar(emp.name, size=38, gender=emp.gender)}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with exp_col:
                with st.expander(label, expanded=is_editing):

                    # ── Expanded detail row ───────────────────────────────────
                    info_col, btn_col = st.columns([6, 1])

                    with info_col:
                        big_av_col, detail_col = st.columns([0.6, 5])
                        with big_av_col:
                            st.markdown(
                                employee_avatar(emp.name, size=52, gender=emp.gender),
                                unsafe_allow_html=True,
                            )
                        with detail_col:
                            st.markdown(f"### {emp.name}")
                            gender_label = emp.gender.capitalize() if emp.gender else "—"
                            st.markdown(
                                f'<span style="color:{TEXT_MID};font-size:0.875rem;line-height:2.2;">'
                                f'📅 &nbsp;Started: <b>{emp.employment_date or "—"}</b>'
                                f'&nbsp;&nbsp;&nbsp;'
                                f'⚧ &nbsp;Gender: <b>{gender_label}</b>'
                                f'&nbsp;&nbsp;&nbsp;'
                                f'💰 &nbsp;Threshold: <b>${thresh:,.0f}</b>'
                                f'&nbsp;&nbsp;&nbsp;'
                                f'📁 &nbsp;Projects: <b>{proj_count}</b>'
                                f'</span>',
                                unsafe_allow_html=True,
                            )

                    with btn_col:
                        st.markdown("<div style='padding-top:14px;'>", unsafe_allow_html=True)
                        if st.button(
                            "✕ Close" if is_editing else "✏️ Edit",
                            key=f"toggle_emp_{emp.id}",
                            use_container_width=True,
                            type="secondary",
                        ):
                            st.session_state.editing_emp_id = None if is_editing else emp.id
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

                    # ── Inline edit form ──────────────────────────────────────
                    if is_editing:
                        st.divider()
                        with st.form(f"edit_emp_{emp.id}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                new_name = st.text_input("Full Name", value=emp.name)
                                new_date = st.date_input("Start Date", value=emp.employment_date)
                                gender_opts = ["Male", "Female", "Other"]
                                cur_idx = gender_opts.index(emp.gender.capitalize()) if emp.gender else 0
                                new_gender = st.selectbox("Gender", gender_opts,
                                                          index=cur_idx, key=f"gender_{emp.id}")
                            with col2:
                                new_thresh = st.number_input(
                                    "Commission Threshold ($)", min_value=0.0,
                                    value=float(cycle.applicable_threshold) if cycle else 20000.0,
                                    step=1000.0, key=f"thresh_{emp.id}",
                                )
                                new_carry = st.number_input(
                                    "Threshold Carryforward ($)", min_value=0.0,
                                    value=float(cycle.threshold_carryforward) if cycle else 0.0,
                                    step=1000.0, key=f"carry_{emp.id}",
                                )
                            col_save, col_del = st.columns([4, 1])
                            with col_save:
                                if st.form_submit_button("Save Changes", type="primary"):
                                    if not new_name.strip():
                                        st.error("Name is required.")
                                    else:
                                        e = session.get(Employee, emp.id)
                                        e.name = new_name.strip()
                                        e.employment_date = new_date
                                        e.gender = new_gender.lower()
                                        if cycle:
                                            c = session.get(CommissionCycle, cycle.id)
                                            c.applicable_threshold = new_thresh
                                            c.threshold_carryforward = new_carry
                                        session.commit()
                                        st.session_state.editing_emp_id = None
                                        st.rerun()
                            with col_del:
                                if st.form_submit_button("🗑 Delete"):
                                    if proj_count > 0:
                                        st.error(f"Remove from {proj_count} project(s) first.")
                                    else:
                                        session.query(EmployeePayment).filter_by(employee_id=emp.id).delete()
                                        if cycle:
                                            session.delete(session.get(CommissionCycle, cycle.id))
                                        session.delete(session.get(Employee, emp.id))
                                        session.commit()
                                        st.session_state.editing_emp_id = None
                                        st.rerun()
