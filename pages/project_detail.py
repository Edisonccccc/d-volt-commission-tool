"""Project detail — Team and Collections tabs."""
import datetime
import streamlit as st

from database import Collection, Employee, Project, ProjectAssignment, get_session
from utils import section_title, dist_bar, avatar, employee_avatar, badge, GREEN, GREEN_LIGHT, GREEN_TEXT, TEXT_LIGHT, TEXT_MID


def _net(c: Collection) -> float:
    return c.collection_amount - c.sales_tax - c.referral_fee - c.approved_sales_exp


# ── Team tab ──────────────────────────────────────────────────────────────────

def _render_team(session, project: Project):
    all_employees = session.query(Employee).order_by(Employee.name).all()
    if not all_employees:
        st.info("Add employees in the Employees tab first.")
        return

    assignments = session.query(ProjectAssignment).filter_by(project_id=project.id).all()
    assigned_map = {a.employee_id: a for a in assignments}
    total_dist = sum(a.distribution for a in assignments)

    # Distribution bar
    if assignments:
        dist_data = [(a.employee.name, a.distribution * 100) for a in assignments]
        st.markdown(dist_bar(dist_data), unsafe_allow_html=True)
        if total_dist > 1.001:
            st.error(f"Total is {total_dist*100:.1f}% — exceeds 100%. Please adjust.")
        elif abs(total_dist - 1.0) > 0.001:
            st.caption(f"{(1-total_dist)*100:.1f}% unassigned")
        else:
            st.caption("✓ 100% distributed")
        st.divider()

    # Employee rows
    editing_id = st.session_state.get("editing_team_emp_id")

    section_title("Team Members")
    for emp in all_employees:
        a = assigned_map.get(emp.id)

        col_avatar, col_name, col_dist, col_btn = st.columns([0.5, 4, 2, 2])
        col_avatar.markdown(employee_avatar(emp.name, gender=emp.gender), unsafe_allow_html=True)
        col_name.markdown(f"**{emp.name}**")

        if a:
            col_dist.markdown(
                badge(f"{a.distribution*100:.1f}%", "blue"),
                unsafe_allow_html=True,
            )
        else:
            col_dist.markdown(badge("Unassigned", "gray"), unsafe_allow_html=True)

        if editing_id == emp.id:
            with st.form(f"edit_team_{emp.id}"):
                ecol1, ecol2, ecol3 = st.columns([3, 2, 2])
                assigned = ecol1.checkbox("Assign to project", value=(a is not None))
                dist_default = round(a.distribution * 100, 1) if a else round(100.0 / max(len(all_employees), 1), 1)
                new_dist = ecol2.number_input(
                    "Distribution %", min_value=0.0, max_value=100.0,
                    value=dist_default, step=5.0, label_visibility="collapsed",
                )
                s_col, c_col = ecol3.columns(2)
                if s_col.form_submit_button("Save", type="primary"):
                    if assigned:
                        if a:
                            session.get(ProjectAssignment, a.id).distribution = new_dist / 100
                        else:
                            session.add(ProjectAssignment(
                                project_id=project.id, employee_id=emp.id, distribution=new_dist / 100
                            ))
                    elif a:
                        session.delete(session.get(ProjectAssignment, a.id))
                    session.commit()
                    st.session_state.editing_team_emp_id = None
                    st.rerun()
                if c_col.form_submit_button("Cancel"):
                    st.session_state.editing_team_emp_id = None
                    st.rerun()
        else:
            if col_btn.button("Edit", key=f"edit_team_{emp.id}", use_container_width=True):
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

    if collections:
        total_collected = sum(c.collection_amount for c in collections)
        total_net = sum(_net(c) for c in collections)
        pct = (total_collected / project.contract_amount * 100) if project.contract_amount else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Collected", f"${total_collected:,.0f}")
        m2.metric("Total Net Revenue", f"${total_net:,.0f}")
        m3.metric("% of Contract", f"{pct:.1f}%")
        st.divider()

    # ── Add collection ────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:{GREEN_LIGHT};border:1.5px solid {GREEN};border-radius:12px;
        padding:1rem 1.25rem 0.5rem 1.25rem;margin-bottom:1rem;">
        <div style="font-size:0.7rem;font-weight:700;color:{GREEN_TEXT};
            text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.75rem;">
            ➕  New Collection
        </div>
    """, unsafe_allow_html=True)

    with st.form("add_collection_form"):
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("Amount Collected ($)", min_value=0.0, value=0.0, step=1000.0)
            date = st.date_input("Collection Date", value=datetime.date.today())
        with col2:
            tax = st.number_input("Sales Tax ($)", min_value=0.0, value=0.0, step=100.0)
            ref = st.number_input("Referral Fee ($)", min_value=0.0, value=0.0, step=100.0)
            exp = st.number_input("Approved Sales Exp ($)", min_value=0.0, value=0.0, step=100.0)
        if st.form_submit_button("Add Collection", type="primary"):
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

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

    # ── Collection history ────────────────────────────────────────────────
    if not collections:
        st.markdown(f"""
        <div style="text-align:center;padding:2rem 1rem;background:white;
            border:1px solid #E5E7EB;border-radius:12px;color:{TEXT_LIGHT};">
            No collections yet. Add the first one above.
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown(f"""
    <div style="background:white;border:1px solid #E5E7EB;border-radius:12px;
        padding:1rem 1.25rem 0.25rem 1.25rem;">
        <div style="font-size:0.7rem;font-weight:700;color:{TEXT_LIGHT};
            text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.75rem;">
            Collection History  ·  {len(collections)} record{"s" if len(collections) != 1 else ""}
        </div>
    """, unsafe_allow_html=True)

    for c in collections:
        net = _net(c)
        with st.expander(f"**{c.collection_date}**  ·  ${c.collection_amount:,.0f} collected  ·  ${net:,.0f} net"):
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
                    if st.form_submit_button("Save Changes", type="primary"):
                        obj = session.get(Collection, c.id)
                        obj.collection_amount = na
                        obj.collection_date = nd
                        obj.sales_tax = nt
                        obj.referral_fee = nr
                        obj.approved_sales_exp = ne
                        session.commit()
                        st.rerun()
                with col_d:
                    if st.form_submit_button("Delete"):
                        session.delete(session.get(Collection, c.id))
                        session.commit()
                        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ── Main render ───────────────────────────────────────────────────────────────

def render(project_id: int):
    with get_session() as session:
        project = session.get(Project, project_id)
        if project is None:
            st.error("Project not found.")
            return

        # Back + header
        back, spacer = st.columns([1, 6])
        with back:
            if st.button("← Back", type="secondary"):
                st.session_state.page = "projects"
                st.session_state.selected_project_id = None
                st.rerun()

        total_collected = sum(c.collection_amount for c in project.collections)
        pct = (total_collected / project.contract_amount * 100) if project.contract_amount else 0

        h_left, h_right = st.columns([5, 1])
        with h_left:
            st.markdown(f"## {project.customer or 'Unnamed Project'}")
            sub = []
            if project.project_no:
                sub.append(project.project_no)
            if project.description:
                sub.append(project.description)
            if sub:
                st.caption("  ·  ".join(sub))
        with h_right:
            if st.button("✏️ Edit Project", key="edit_proj_toggle"):
                st.session_state["editing_project"] = not st.session_state.get("editing_project", False)

        m1, m2, m3 = st.columns(3)
        m1.metric("Contract Amount", f"${project.contract_amount:,.0f}")
        m2.metric("Total Collected", f"${total_collected:,.0f}")
        m3.metric("Collection Progress", f"{pct:.1f}%")

        if st.session_state.get("editing_project"):
            st.divider()
            with st.form("edit_project_form"):
                col1, col2 = st.columns(2)
                with col1:
                    nc = st.text_input("Customer", value=project.customer or "")
                    np_val = st.text_input("Project No.", value=project.project_no or "")
                with col2:
                    nd = st.text_input("Description", value=project.description or "")
                    nca = st.number_input("Contract Amount ($)", min_value=0.0, value=float(project.contract_amount), step=1000.0)
                col_s, col_del = st.columns([3, 1])
                with col_s:
                    if st.form_submit_button("Save Changes", type="primary"):
                        p = session.get(Project, project_id)
                        p.customer = nc or None
                        p.project_no = np_val or None
                        p.description = nd or None
                        p.contract_amount = nca
                        session.commit()
                        st.session_state["editing_project"] = False
                        st.rerun()
                with col_del:
                    if st.form_submit_button("Delete Project"):
                        session.delete(session.get(Project, project_id))
                        session.commit()
                        st.session_state.page = "projects"
                        st.session_state.selected_project_id = None
                        st.rerun()

        st.divider()

        tab_team, tab_collections = st.tabs(["👥  Team", "💵  Collections"])
        with tab_team:
            _render_team(session, project)
        with tab_collections:
            _render_collections(session, project)
