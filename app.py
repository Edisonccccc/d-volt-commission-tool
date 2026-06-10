import streamlit as st
from database import init_db, Project, get_session

init_db()

st.set_page_config(
    page_title="D Volt Co — Commission System",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    "<style>[data-testid='collapsedControl']{display:none}section[data-testid='stSidebar']{display:none}</style>",
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────────────
if "selected_project_id" not in st.session_state:
    st.session_state.selected_project_id = None
if "selected_employee_id" not in st.session_state:
    st.session_state.selected_employee_id = None
# "projects" | "project_detail" | "employees" | "settings"
if "page" not in st.session_state:
    st.session_state.page = "projects"

# ── Header ────────────────────────────────────────────────────────────────────
header_left, header_right = st.columns([8, 1])
with header_left:
    st.markdown("### D Volt Co — Commission System")
with header_right:
    with st.popover("☰", use_container_width=True):
        if st.button("⚙  Bracket Settings", use_container_width=True):
            st.session_state.page = "settings"
            st.rerun()

# ── Main tabs ─────────────────────────────────────────────────────────────────
tab_projects, tab_employees, tab_commission = st.tabs(["Projects", "Employees", "Commission"])

# ── Projects tab ──────────────────────────────────────────────────────────────
with tab_projects:
    if st.session_state.page == "project_detail" and st.session_state.selected_project_id:
        from pages import project_detail
        project_detail.render(st.session_state.selected_project_id)

    elif st.session_state.page == "settings":
        from pages import settings
        settings.render()

    else:
        st.session_state.page = "projects"

        with get_session() as s:
            projects = s.query(Project).order_by(Project.customer, Project.project_no).all()
            proj_data = [
                {
                    "id": p.id,
                    "customer": p.customer or "Unnamed",
                    "project_no": p.project_no or "—",
                    "description": p.description or "",
                    "contract_amount": p.contract_amount,
                    "num_employees": len(p.assignments),
                    "num_collections": len(p.collections),
                    "total_collected": sum(c.collection_amount for c in p.collections),
                }
                for p in projects
            ]

        with st.expander("➕ New Project", expanded=not proj_data):
            with st.form("new_project_form"):
                col1, col2 = st.columns(2)
                with col1:
                    customer = st.text_input("Customer Name")
                    project_no = st.text_input("Project / PO Number")
                with col2:
                    description = st.text_input("Description")
                    contract_amount = st.number_input("Contract Amount ($)", min_value=0.0, value=0.0, step=10000.0)
                if st.form_submit_button("Create Project", type="primary"):
                    if not customer.strip():
                        st.error("Customer name is required.")
                    else:
                        with get_session() as s:
                            proj = Project(
                                customer=customer.strip(),
                                project_no=project_no or None,
                                description=description or None,
                                contract_amount=contract_amount,
                            )
                            s.add(proj)
                            s.commit()
                            new_pid = proj.id
                        st.session_state.selected_project_id = new_pid
                        st.session_state.page = "project_detail"
                        st.rerun()

        if not proj_data:
            st.markdown("No projects yet. Create one above.")
        else:
            cols = st.columns(3)
            for i, p in enumerate(proj_data):
                with cols[i % 3]:
                    with st.container(border=True):
                        st.markdown(f"**{p['customer']}**")
                        st.caption(
                            f"{p['project_no']}  ·  {p['description']}"
                            if p['description'] else p['project_no']
                        )
                        st.markdown(f"Contract: **${p['contract_amount']:,.0f}**")
                        st.markdown(
                            f"Collected: ${p['total_collected']:,.0f}  ·  "
                            f"{p['num_employees']} employee{'s' if p['num_employees'] != 1 else ''}  ·  "
                            f"{p['num_collections']} collection{'s' if p['num_collections'] != 1 else ''}"
                        )
                        if st.button("Open", key=f"open_proj_{p['id']}", use_container_width=True, type="primary"):
                            st.session_state.selected_project_id = p["id"]
                            st.session_state.page = "project_detail"
                            st.rerun()

# ── Employees tab ────────────────────────────────────────────────────────────
with tab_employees:
    from pages import employees
    employees.render()

# ── Commission tab ────────────────────────────────────────────────────────────
with tab_commission:
    from pages import employee_statement
    employee_statement.render(st.session_state.get("selected_employee_id"))
