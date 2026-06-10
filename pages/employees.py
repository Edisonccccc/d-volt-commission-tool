"""
Employees tab — manage employees and their commission settings.
"""
import datetime
from typing import Optional

import streamlit as st

from database import Employee, CommissionCycle, ProjectAssignment, EmployeePayment, get_session


def render():
    with get_session() as session:
        employees = session.query(Employee).order_by(Employee.name).all()

        # Add employee form
        with st.expander("➕ Add Employee", expanded=not employees):
            with st.form("add_employee_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Full Name")
                    emp_date = st.date_input("Start Date", value=datetime.date.today())
                with col2:
                    threshold = st.number_input(
                        "Commission Threshold ($)", min_value=0.0, value=20000.0, step=1000.0,
                        help="Minimum cumulative net revenue before any commission is paid out.",
                    )
                    carryforward = st.number_input(
                        "Threshold Carryforward ($)", min_value=0.0, value=0.0, step=1000.0,
                        help="Revenue already counted from a prior period.",
                    )
                if st.form_submit_button("Add Employee", type="primary"):
                    if not name.strip():
                        st.error("Name is required.")
                    else:
                        emp = Employee(name=name.strip(), employment_date=emp_date)
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
                        st.success(f"Added {name.strip()}.")
                        st.rerun()

        if not employees:
            st.info("No employees yet. Add one above.")
            return

        st.divider()

        # Employee list
        for emp in employees:
            cycle = session.query(CommissionCycle).filter_by(employee_id=emp.id).first()
            proj_count = session.query(ProjectAssignment).filter_by(employee_id=emp.id).count()

            with st.expander(f"**{emp.name}**  ·  {proj_count} project{'s' if proj_count != 1 else ''}"):
                with st.form(f"edit_emp_{emp.id}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_name = st.text_input("Full Name", value=emp.name)
                        new_date = st.date_input("Start Date", value=emp.employment_date)
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
                        if st.form_submit_button("Save", type="primary"):
                            if not new_name.strip():
                                st.error("Name is required.")
                            else:
                                e = session.get(Employee, emp.id)
                                e.name = new_name.strip()
                                e.employment_date = new_date
                                if cycle:
                                    c = session.get(CommissionCycle, cycle.id)
                                    c.applicable_threshold = new_thresh
                                    c.threshold_carryforward = new_carry
                                session.commit()
                                st.success("Saved.")
                                st.rerun()
                    with col_del:
                        if st.form_submit_button("Delete", type="secondary"):
                            if proj_count > 0:
                                st.error(f"Remove from {proj_count} project(s) first.")
                            else:
                                # Delete payments and cycle first
                                session.query(EmployeePayment).filter_by(employee_id=emp.id).delete()
                                if cycle:
                                    session.delete(session.get(CommissionCycle, cycle.id))
                                session.delete(session.get(Employee, emp.id))
                                session.commit()
                                st.rerun()
