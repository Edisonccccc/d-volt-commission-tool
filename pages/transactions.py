import streamlit as st
import datetime
import pandas as pd

from database import Employee, CommissionCycle, Transaction, get_session


def _cycle_label(cycle: CommissionCycle) -> str:
    return (
        f"{cycle.employee.name} | "
        f"{cycle.start_date or '?'} → {cycle.end_date or '?'}"
    )


def render():
    st.header("Transactions")

    with get_session() as session:
        cycles = (
            session.query(CommissionCycle)
            .join(Employee)
            .order_by(Employee.name, CommissionCycle.start_date.desc())
            .all()
        )

        if not cycles:
            st.warning("Create a commission cycle first.")
            return

        cycle_labels = [_cycle_label(c) for c in cycles]
        selected_label = st.selectbox("Select Cycle", cycle_labels)
        selected_cycle = cycles[cycle_labels.index(selected_label)]
        cycle_id = selected_cycle.id

        txns = (
            session.query(Transaction)
            .filter_by(cycle_id=cycle_id)
            .order_by(Transaction.collection_date, Transaction.id)
            .all()
        )

        st.divider()

        # --- Add transaction ---
        with st.expander("Add Transaction", expanded=not txns):
            with st.form("add_txn"):
                col1, col2 = st.columns(2)
                with col1:
                    customer = st.text_input("Customer")
                    project_no = st.text_input("Project No.")
                    product_desc = st.text_input("Product Description")
                    qty = st.number_input("Qty", min_value=0.0, value=0.0, step=1.0)
                with col2:
                    contract_amount = st.number_input("Contract/PO Amount ($)", min_value=0.0, value=0.0, step=1000.0)
                    collection_amount = st.number_input("Collection Amount ($)", min_value=0.0, value=0.0, step=1000.0)
                    collection_date = st.date_input("Collection Date", value=datetime.date.today())
                    commission_weight = st.number_input("Commission Weight", min_value=0.0, value=1.0, step=0.1)

                st.markdown("**Deductions**")
                col3, col4, col5 = st.columns(3)
                with col3:
                    sales_tax = st.number_input("Sales Tax ($)", min_value=0.0, value=0.0, step=100.0)
                with col4:
                    referral_fee = st.number_input("Referral Fee ($)", min_value=0.0, value=0.0, step=100.0)
                with col5:
                    approved_exp = st.number_input("Approved Sales Exp ($)", min_value=0.0, value=0.0, step=100.0)

                st.markdown("**Settlement / Advances**")
                col6, col7 = st.columns(2)
                with col6:
                    settlement_amount = st.number_input("Settlement Amount ($)", value=0.0, step=100.0)
                    settlement_date = st.date_input("Settlement Date", value=None)
                with col7:
                    advance_paid = st.number_input("Advance Paid ($)", value=0.0, step=100.0)
                    advance_date = st.date_input("Advance Date", value=None)

                if st.form_submit_button("Add Transaction"):
                    session.add(Transaction(
                        cycle_id=cycle_id,
                        customer=customer or None,
                        project_no=project_no or None,
                        product_description=product_desc or None,
                        qty=qty or None,
                        contract_amount=contract_amount,
                        collection_amount=collection_amount,
                        collection_date=collection_date,
                        sales_tax=sales_tax,
                        referral_fee=referral_fee,
                        approved_sales_exp=approved_exp,
                        commission_weight=commission_weight,
                        settlement_amount=settlement_amount,
                        settlement_date=settlement_date,
                        advance_paid=advance_paid,
                        advance_date=advance_date,
                    ))
                    session.commit()
                    st.success("Transaction added.")
                    st.rerun()

        # --- List transactions ---
        if not txns:
            st.info("No transactions in this cycle yet.")
            return

        st.subheader(f"Transactions ({len(txns)})")

        for txn in txns:
            label = (
                f"{txn.collection_date or '?'} | "
                f"{txn.customer or '—'} | "
                f"Collected: ${txn.collection_amount:,.2f}"
            )
            with st.expander(label, expanded=False):
                with st.form(f"edit_txn_{txn.id}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_customer = st.text_input("Customer", value=txn.customer or "")
                        new_project = st.text_input("Project No.", value=txn.project_no or "")
                        new_desc = st.text_input("Product Description", value=txn.product_description or "")
                        new_qty = st.number_input("Qty", min_value=0.0, value=float(txn.qty or 0), step=1.0, key=f"qty_{txn.id}")
                    with col2:
                        new_contract = st.number_input("Contract/PO Amount ($)", min_value=0.0, value=float(txn.contract_amount or 0), step=1000.0, key=f"ca_{txn.id}")
                        new_collection = st.number_input("Collection Amount ($)", min_value=0.0, value=float(txn.collection_amount), step=1000.0, key=f"col_{txn.id}")
                        new_cdate = st.date_input("Collection Date", value=txn.collection_date, key=f"cd_{txn.id}")
                        new_weight = st.number_input("Commission Weight", min_value=0.0, value=float(txn.commission_weight), step=0.1, key=f"wt_{txn.id}")

                    st.markdown("**Deductions**")
                    col3, col4, col5 = st.columns(3)
                    with col3:
                        new_tax = st.number_input("Sales Tax ($)", min_value=0.0, value=float(txn.sales_tax), step=100.0, key=f"tx_{txn.id}")
                    with col4:
                        new_ref = st.number_input("Referral Fee ($)", min_value=0.0, value=float(txn.referral_fee), step=100.0, key=f"rf_{txn.id}")
                    with col5:
                        new_exp = st.number_input("Approved Sales Exp ($)", min_value=0.0, value=float(txn.approved_sales_exp), step=100.0, key=f"ae_{txn.id}")

                    st.markdown("**Settlement / Advances**")
                    col6, col7 = st.columns(2)
                    with col6:
                        new_settle = st.number_input("Settlement Amount ($)", value=float(txn.settlement_amount), step=100.0, key=f"sa_{txn.id}")
                        new_sdate = st.date_input("Settlement Date", value=txn.settlement_date, key=f"sd_{txn.id}")
                    with col7:
                        new_adv = st.number_input("Advance Paid ($)", value=float(txn.advance_paid), step=100.0, key=f"ap_{txn.id}")
                        new_adate = st.date_input("Advance Date", value=txn.advance_date, key=f"ad_{txn.id}")

                    col_save, col_del = st.columns([3, 1])
                    with col_save:
                        if st.form_submit_button("Save"):
                            t = session.get(Transaction, txn.id)
                            t.customer = new_customer or None
                            t.project_no = new_project or None
                            t.product_description = new_desc or None
                            t.qty = new_qty or None
                            t.contract_amount = new_contract
                            t.collection_amount = new_collection
                            t.collection_date = new_cdate
                            t.commission_weight = new_weight
                            t.sales_tax = new_tax
                            t.referral_fee = new_ref
                            t.approved_sales_exp = new_exp
                            t.settlement_amount = new_settle
                            t.settlement_date = new_sdate
                            t.advance_paid = new_adv
                            t.advance_date = new_adate
                            session.commit()
                            st.success("Saved.")
                            st.rerun()

                    with col_del:
                        if st.button("Delete", key=f"del_txn_{txn.id}", type="secondary"):
                            session.delete(session.get(Transaction, txn.id))
                            session.commit()
                            st.rerun()
