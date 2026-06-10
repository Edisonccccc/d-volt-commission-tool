import streamlit as st
import datetime

from database import Employee, CommissionCycle, Transaction, get_session


def render():
    st.header("Commission Cycles")

    with get_session() as session:
        employees = session.query(Employee).order_by(Employee.name).all()

        if not employees:
            st.warning("Add employees first before creating cycles.")
            return

        emp_map = {e.name: e.id for e in employees}

        # --- Add cycle ---
        with st.expander("Add New Cycle", expanded=False):
            with st.form("add_cycle"):
                emp_name = st.selectbox("Employee", list(emp_map.keys()))
                col1, col2 = st.columns(2)
                with col1:
                    start = st.date_input("Cycle Start Date", value=datetime.date.today().replace(month=4, day=1))
                with col2:
                    end = st.date_input("Cycle End Date", value=datetime.date.today().replace(month=4, day=1).replace(year=datetime.date.today().year + 1) - datetime.timedelta(days=1))
                col3, col4 = st.columns(2)
                with col3:
                    threshold = st.number_input("Applicable Threshold ($)", min_value=0.0, value=20000.0, step=1000.0)
                with col4:
                    carryforward = st.number_input("Threshold Carryforward ($)", min_value=0.0, value=0.0, step=1000.0)
                if st.form_submit_button("Create Cycle"):
                    session.add(CommissionCycle(
                        employee_id=emp_map[emp_name],
                        start_date=start,
                        end_date=end,
                        applicable_threshold=threshold,
                        threshold_carryforward=carryforward,
                    ))
                    session.commit()
                    st.success("Cycle created.")
                    st.rerun()

        st.divider()

        # --- List cycles ---
        cycles = (
            session.query(CommissionCycle)
            .join(Employee)
            .order_by(Employee.name, CommissionCycle.start_date.desc())
            .all()
        )

        if not cycles:
            st.info("No cycles yet.")
            return

        for cycle in cycles:
            label = (
                f"{cycle.employee.name} | "
                f"{cycle.start_date or '?'} → {cycle.end_date or '?'} | "
                f"Threshold: ${cycle.commission_threshold:,.0f}"
            )
            with st.expander(label, expanded=False):
                with st.form(f"edit_cycle_{cycle.id}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_start = st.date_input("Start Date", value=cycle.start_date, key=f"cs_{cycle.id}")
                    with col2:
                        new_end = st.date_input("End Date", value=cycle.end_date, key=f"ce_{cycle.id}")
                    col3, col4 = st.columns(2)
                    with col3:
                        new_threshold = st.number_input(
                            "Applicable Threshold ($)", min_value=0.0,
                            value=float(cycle.applicable_threshold), step=1000.0, key=f"ct_{cycle.id}"
                        )
                    with col4:
                        new_carryforward = st.number_input(
                            "Threshold Carryforward ($)", min_value=0.0,
                            value=float(cycle.threshold_carryforward), step=1000.0, key=f"cf_{cycle.id}"
                        )
                    col_save, col_del = st.columns([3, 1])
                    with col_save:
                        if st.form_submit_button("Save"):
                            c = session.get(CommissionCycle, cycle.id)
                            c.start_date = new_start
                            c.end_date = new_end
                            c.applicable_threshold = new_threshold
                            c.threshold_carryforward = new_carryforward
                            session.commit()
                            st.success("Saved.")
                            st.rerun()

                txn_count = session.query(Transaction).filter_by(cycle_id=cycle.id).count()
                st.caption(f"{txn_count} transaction(s)")
                if st.button("Delete Cycle", key=f"del_cycle_{cycle.id}", type="secondary"):
                    if txn_count > 0:
                        st.error("Delete all transactions in this cycle first.")
                    else:
                        session.delete(session.get(CommissionCycle, cycle.id))
                        session.commit()
                        st.rerun()
