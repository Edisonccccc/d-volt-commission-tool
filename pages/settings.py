import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session

from database import CommissionBracket, get_session


def render():
    if st.button("← Back to Projects", type="secondary"):
        st.session_state.page = "projects"
        st.rerun()

    st.header("Commission Bracket Settings")
    st.caption("Define the tiered marginal commission rates applied to cumulative net revenue.")

    with get_session() as session:
        brackets = session.query(CommissionBracket).order_by(CommissionBracket.sort_order).all()

        # Build display dataframe
        rows = []
        prev_upper = 0
        for b in brackets:
            lower_label = f"${prev_upper:,.0f}"
            upper_label = f"${b.upper_bound:,.0f}" if b.upper_bound is not None else "∞"
            rows.append({
                "id": b.id,
                "Revenue Range": f"{lower_label} – {upper_label}",
                "Rate (%)": round(b.rate * 100, 4),
                "Upper Bound ($)": b.upper_bound if b.upper_bound is not None else "",
            })
            prev_upper = b.upper_bound if b.upper_bound is not None else prev_upper

        df = pd.DataFrame(rows)

        st.subheader("Current Brackets")
        st.dataframe(df[["Revenue Range", "Rate (%)"]], use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Edit Brackets")
        st.info("Replace all brackets with new values. Brackets are applied in order; the last bracket has no upper bound (applies to all remaining revenue).")

        edit_df = pd.DataFrame([
            {
                "Upper Bound ($) — leave blank for last tier": b.upper_bound if b.upper_bound is not None else "",
                "Rate (%)": round(b.rate * 100, 4),
            }
            for b in brackets
        ])

        edited = st.data_editor(
            edit_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "Upper Bound ($) — leave blank for last tier": st.column_config.NumberColumn(min_value=0),
                "Rate (%)": st.column_config.NumberColumn(min_value=0, max_value=100, format="%.4f %%"),
            },
        )

        if st.button("Save Brackets", type="primary"):
            # Validate: only last row may have blank upper bound
            rows_data = edited.to_dict("records")
            valid = True
            for i, row in enumerate(rows_data):
                ub = row.get("Upper Bound ($) — leave blank for last tier")
                is_last = i == len(rows_data) - 1
                if (ub == "" or ub is None or pd.isna(ub)) and not is_last:
                    st.error(f"Row {i+1}: Only the last bracket can have a blank upper bound.")
                    valid = False
                    break
                rate = row.get("Rate (%)")
                if rate is None or pd.isna(rate) or rate < 0:
                    st.error(f"Row {i+1}: Rate must be a non-negative number.")
                    valid = False
                    break

            if valid and rows_data:
                session.query(CommissionBracket).delete()
                for i, row in enumerate(rows_data):
                    ub_raw = row.get("Upper Bound ($) — leave blank for last tier")
                    upper = None if (ub_raw == "" or ub_raw is None or pd.isna(ub_raw)) else float(ub_raw)
                    rate = float(row["Rate (%)"]) / 100
                    session.add(CommissionBracket(upper_bound=upper, rate=rate, sort_order=i))
                session.commit()
                st.success("Brackets saved.")
                st.rerun()
