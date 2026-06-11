import streamlit as st
from database import init_db, Project, get_session
from utils import inject_css, page_header, project_card_html

init_db()

st.set_page_config(
    page_title="D Volt Co — Commission System",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()

# ── Session state ─────────────────────────────────────────────────────────────
if "selected_project_id" not in st.session_state:
    st.session_state.selected_project_id = None
if "selected_employee_id" not in st.session_state:
    st.session_state.selected_employee_id = None
if "page" not in st.session_state:
    st.session_state.page = "projects"
if "show_new_project" not in st.session_state:
    st.session_state.show_new_project = False
if "show_new_employee" not in st.session_state:
    st.session_state.show_new_employee = False

# ── Header ────────────────────────────────────────────────────────────────────
h_left, h_right = st.columns([9, 1])
with h_left:
    page_header("D Volt Co", "Commission Management System")
with h_right:
    st.markdown("<div style='padding-top:18px;'>", unsafe_allow_html=True)
    with st.popover("☰", use_container_width=True):
        if st.button("⚙  Bracket Settings", use_container_width=True):
            st.session_state.page = "settings"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ── Main tabs ─────────────────────────────────────────────────────────────────
tab_projects, tab_employees, tab_commission = st.tabs(["📁  Projects", "👥  Employees", "💰  Commission"])

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

        from utils import GREEN, GREEN_LIGHT, GREEN_TEXT, TEXT_LIGHT, TEXT_MID

        # ── Header bar with New Project toggle ───────────────────────────
        hdr_left, hdr_right = st.columns([6, 1])
        with hdr_left:
            st.markdown(f"""
            <div style="font-size:0.72rem;font-weight:800;color:{TEXT_LIGHT};
                text-transform:uppercase;letter-spacing:0.1em;padding-top:6px;">
                📁 &nbsp; Projects &nbsp;
                <span style="background:#F3F4F6;color:#6B7280;padding:1px 8px;
                    border-radius:20px;font-size:0.7rem;">{len(proj_data)}</span>
            </div>
            """, unsafe_allow_html=True)
        with hdr_right:
            btn_label = "✕ Cancel" if st.session_state.show_new_project else "➕ New"
            if st.button(btn_label, type="primary" if not st.session_state.show_new_project else "secondary",
                         use_container_width=True):
                st.session_state.show_new_project = not st.session_state.show_new_project
                st.rerun()

        # ── Collapsible new project form ──────────────────────────────────
        if st.session_state.show_new_project:
            with st.container(border=True):
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
                            st.session_state.show_new_project = False
                            st.session_state.selected_project_id = new_pid
                            st.session_state.page = "project_detail"
                            st.rerun()
            st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)

        # ── Project list ──────────────────────────────────────────────────
        if not proj_data:
            st.markdown(f"""
            <div style="text-align:center;padding:3rem 1rem;color:{TEXT_LIGHT};
                background:white;border-radius:12px;border:1px solid #E5E7EB;margin-top:1rem;">
                <div style="font-size:2.5rem;margin-bottom:12px;">📁</div>
                <div style="font-size:1rem;font-weight:600;color:#6B7280;">No projects yet</div>
                <div style="font-size:0.85rem;margin-top:4px;">Click <b>➕ New</b> above to create your first project.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            cols = st.columns(3)
            for i, p in enumerate(proj_data):
                with cols[i % 3]:
                    with st.container(border=True):
                        st.markdown(project_card_html(
                            p["customer"], p["project_no"], p["description"],
                            p["contract_amount"], p["total_collected"], p["num_employees"],
                        ), unsafe_allow_html=True)
                        if st.button("Open →", key=f"open_proj_{p['id']}", use_container_width=True, type="primary"):
                            st.session_state.selected_project_id = p["id"]
                            st.session_state.page = "project_detail"
                            st.rerun()

# ── Employees tab ─────────────────────────────────────────────────────────────
with tab_employees:
    from pages import employees
    employees.render()

# ── Commission tab ────────────────────────────────────────────────────────────
with tab_commission:
    from pages import employee_statement
    employee_statement.render(st.session_state.get("selected_employee_id"))
