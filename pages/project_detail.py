"""
Project detail page — two tabs: Team (assignments) and Collections.
"""
import datetime
import streamlit as st

from database import (
    Collection, Employee, Project, ProjectAssignment, get_session,
)


def _net(c: Collection) -> float:
    return c.collection_amount - c.sales_tax - c.referral_fee - c.approved_sales_exp


# ── Team tab ──────────────────────────────────────────────────────────────────

def _render_team(session, project: Project):
    all_employees = session.query(Employee).order_by(Employee.name).all()
    if not all_employees:
        st.warning("Add employees first in the Employees tab.")
        return

    assignments = (
        session.query(ProjectAssignment)
        .filter_by(project_id=project.id)
        .all()
    )
    assigned_map = {a.employee_id: a for a in assignments}
    total_dist = sum(a.distribution for a in assignments)

    # Distribution summary
    if total_dist > 1.001:
        st.error(f"Total distribution is {total_dist*100:.1f}% — exceeds 100%. Please adjust.")
    elif assignments:
        remaining = (1.0 - total_dist) * 100
        label = "✓ Fully distributed" if abs(total_dist - 1.0) <= 0.001 else f"{remaining:.1f}% unassigned"
        st.caption(f"Total assigned: **{total_dist*100:.1f}%** — {label}")

    st.divider()

    # One row per employee
    editing_id = st.session_state.get("editing_team_emp_id")

    for emp in all_employees:
        a = assigned_map.get(emp.id)
        col_name, col_dist, col_btn = st.columns([4, 2, 2])

        col_name.write(emp.name)
        col_dist.write(f"{a.distribution*100:.1f}%" if a else "—")

        if editing_id == emp.id:
            # Inline edit row
            with st.form(f"edit_team_{emp.id}"):
                ecol1, ecol2, ecol3 = st.columns([3, 2, 2])
                assigned = ecol1.checkbox("Assigned", value=(a is not None))
                dist_val = round(a.distribution * 100, 1) if a else round(100.0 / max(len(all_employees), 1), 1)
                new_dist = ecol2.number_input("%", min_value=0.0, max_value=100.0, value=dist_val, step=5.0, label_visibility="collapsed")
                save, cancel = ecol3.columns(2)
                if save.form_submit_button("Save", type="primary"):
                    if assigned:
                        if a:
                            session.get(ProjectAssignment, a.id).distribution = new_dist / 100
                        else:
                            session.add(ProjectAssignment(project_id=project.id, employee_id=emp.id, distribution=new_dist / 100))
                    else:
                        if a:
                            session.delete(session.get(ProjectAssignment, a.id))
                    session.commit()
                    st.session_state.editing_team_emp_id = None
                    st.rerun()
                if cancel.form_submit_button("Cancel"):
                    st.session_state.editing_team_emp_id = None
                    st.rerun()
        else:
            if col_btn.button("Edit", key=f"edit_team_{emp.id}"):
                st.session_state.editing_team_emp_id = emp.id
                st.rerun()


# ── Collections tab ───────────────────────────────────────────────────────────

def _render_collections(session, project: Project):
    collections = (
        session.query(Collection)
        .filter_by(project_id=project.id)
        .order_by(Collection.collection_date, Collection.id)
        .all()
    )

    # Running totals
    if collections:
        total_collected = sum(c.collection_amount for c in collections)
        total_net = sum(_net(c) for c in collections)
        pct = (total_collected / project.contract_amount * 100) if project.contract_amount else 0
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Collected", f"${total_collected:,.2f}")
        m2.metric("Total Net Revenue", f"${total_net:,.2f}")
        m3.metric("% of Contract", f"{pct:.1f}%")
        st.divider()

    # Add collection form
    with st.expander("➕ Add Collection", expanded=not collections):
        with st.form("add_collection_form"):
            col1, col2 = st.columns(2)
            with col1:
                amount = st.number_input("Amount Collected ($)", min_value=0.0, value=0.0, step=1000.0)
                date = st.date_input("Collection Date", value=datetime.date.today())
            with col2:
                tax = st.number_input("Sales Tax ($)", min_value=0.0, value=0.0, step=100.0)
                ref = st.number_input("Referral Fee ($)", min_value=0.0, value=0.0, step=100.0)
                exp = st.number_input("Approved Sales Exp ($)", min_value=0.0, value=0.0, step=100.0)
            if st.form_submit_button("Add", type="primary"):
                session.add(Collection(
                    project_id=project.id,
                    collection_amount=amount,
                    collection_date=date,
                    sales_tax=tax,
                    referral_fee=ref,
                    approved_sales_exp=exp,
                ))
                session.commit()
                st.rerun()

    # List collections
    for c in collections:
        label = f"{c.collection_date or '?'}  ·  Collected: ${c.collection_amount:,.2f}  ·  Net: ${_net(c):,.2f}"
        with st.expander(label):
            with st.form(f"edit_col_{c.id}"):
                col1, col2 = st.columns(2)
                with col1:
                    na = st.number_input("Amount Collected ($)", min_value=0.0, value=float(c.collection_amount), step=1000.0, key=f"ca_{c.id}")
                    nd = st.date_input("Collection Date", value=c.collection_date, key=f"cd_{c.id}")
                with col2:
                    nt = st.number_input("Sales Tax ($)", min_value=0.0, value=float(c.sales_tax), step=100.0, key=f"tx_{c.id}")
                    nr = st.number_input("Referral Fee ($)", min_value=0.0, value=float(c.referral_fee), step=100.0, key=f"rf_{c.id}")
                    ne = st.number_input("Approved Sales Exp ($)", min_value=0.0, value=float(c.approved_sales_exp), step=100.0, key=f"ae_{c.id}")
                col_s, col_d = st.columns([4, 1])
                with col_s:
                    if st.form_submit_button("Save", type="primary"):
                        obj = session.get(Collection, c.id)
                        obj.collection_amount = na
                        obj.collection_date = nd
                        obj.sales_tax = nt
                        obj.referral_fee = nr
                        obj.approved_sales_exp = ne
                        session.commit()
                        st.rerun()
            if st.button("Delete", key=f"del_col_{c.id}", type="secondary"):
                session.delete(session.get(Collection, c.id))
                session.commit()
                st.rerun()


# ── Main render ───────────────────────────────────────────────────────────────

def render(project_id: int):
    with get_session() as session:
        project = session.get(Project, project_id)
        if project is None:
            st.error("Project not found.")
            return

        # Header
        if st.button("← Projects"):
            st.session_state.page = "projects"
            st.session_state.selected_project_id = None
            st.rerun()

        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        col1.markdown(f"### {project.customer or 'Unnamed Project'}")
        col2.metric("Project No.", project.project_no or "—")
        col3.metric("Contract Amount", f"${project.contract_amount:,.2f}")

        with col4:
            if st.button("Edit", key="edit_proj_toggle"):
                st.session_state["editing_project"] = not st.session_state.get("editing_project", False)

        if st.session_state.get("editing_project"):
            with st.form("edit_project_form"):
                nc = st.text_input("Customer", value=project.customer or "")
                np = st.text_input("Project No.", value=project.project_no or "")
                nd = st.text_input("Description", value=project.description or "")
                nca = st.number_input("Contract Amount ($)", min_value=0.0, value=float(project.contract_amount), step=1000.0)
                col_s, col_del = st.columns([3, 1])
                with col_s:
                    if st.form_submit_button("Save", type="primary"):
                        p = session.get(Project, project_id)
                        p.customer = nc or None
                        p.project_no = np or None
                        p.description = nd or None
                        p.contract_amount = nca
                        session.commit()
                        st.session_state["editing_project"] = False
                        st.rerun()
                with col_del:
                    if st.form_submit_button("Delete Project", type="secondary"):
                        session.delete(session.get(Project, project_id))
                        session.commit()
                        st.session_state.page = "home"
                        st.session_state.get("editing_project", False)
                        st.rerun()

        if project.description:
            st.caption(project.description)

        st.divider()

        tab_team, tab_collections = st.tabs(["Team", "Collections"])
        with tab_team:
            _render_team(session, project)
        with tab_collections:
            _render_collections(session, project)
