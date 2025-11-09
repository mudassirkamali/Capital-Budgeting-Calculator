import streamlit as st
import capital_budgeting_logic as logic
from typing import Dict, Any, Tuple

# Set page configuration
st.set_page_config(layout="wide", page_title="Capital Budgeting Calculator")

# --- Main Title ---
st.title("Capital Budgeting & Project Evaluation")
st.markdown("This tool calculates all key metrics (NPV, IRR, Payback) for your project.")

# --- Sidebar for Inputs ---
st.sidebar.header("Project Inputs")

initial_investment = st.sidebar.number_input(
    "Initial Investment ($)",
    min_value=0.01,
    value=100000.0,
    step=1000.0,
    format="%.2f",
    help="Enter the total cost of the project at Year 0 as a positive number."
)

discount_rate = st.sidebar.number_input(
    "Discount Rate / WACC (%)",
    min_value=-99.0,
    value=10.0,
    step=1.0,
    format="%.2f",
    help="Enter the weighted average cost of capital or required rate of return (e.g., 10 for 10%)."
)

cash_flows_str = st.sidebar.text_area(
    "Future Cash Flows (one per line, per year)",
    value="25000\n30000\n35000\n40000\n45000",
    height=200,
    help="Enter the expected cash flow for each year (Year 1, Year 2, etc.) on a new line."
)

# --- Main Area for Results ---
if st.sidebar.button("Calculate Metrics"):
    try:
        # --- 1. Parse and Validate Inputs ---
        rate = discount_rate / 100.0  # Convert percentage to decimal

        future_cash_flows = []
        for line in cash_flows_str.splitlines():
            line = line.strip()
            if line:
                future_cash_flows.append(float(line))

        if not future_cash_flows:
            raise ValueError("At least one Future Cash Flow is required.")

        # --- 2. Call Logic Function ---
        results = logic.calculate_all_metrics(rate, initial_investment, future_cash_flows)

        # --- 3. Display Results ---
        st.header("Project Evaluation Results")

        # Create columns for key metrics
        col1, col2, col3 = st.columns(3)

        npv_val = results['npv']
        col1.metric(
            label="Net Present Value (NPV)",
            value=f"${npv_val:,.2f}",
            delta="Positive NPV" if npv_val > 0 else "Negative NPV"
        )

        irr_val = results['irr']
        irr_text = "N/A"
        irr_delta = None
        if isinstance(irr_val, float):
            irr_text = f"{irr_val * 100:.2f}%"
            irr_delta = f"{((irr_val - rate) * 100):.2f}% vs Rate"

        col2.metric(
            label="Internal Rate of Return (IRR)",
            value=irr_text,
            delta=irr_delta
        )

        pi_val = results['profitability_index']
        pi_text = "N/A"
        pi_delta = None
        if isinstance(pi_val, float):
            pi_text = f"{pi_val:.3f}"
            pi_delta = "Pass" if pi_val > 1 else "Fail"

        col3.metric(
            label="Profitability Index (PI)",
            value=pi_text,
            delta=pi_delta
        )

        st.divider()

        # Create columns for payback periods
        col_pb, col_dpb = st.columns(2)
        col_pb.metric(label="Payback Period (Years)", value=str(results['payback_period']))
        col_dpb.metric(label="Discounted Payback (Years)", value=str(results['discounted_payback_period']))

        st.divider()

        # --- 4. Display Decision Text ---
        st.subheader("Decision Analysis")
        decision_text, is_acceptable = get_decision_text(results, rate)

        if is_acceptable:
            st.success(decision_text)
        else:
            st.error(decision_text)

    except ValueError as e:
        # Handle conversion errors (e.g., "abc" in cash flow) or logic errors
        st.error(f"Input Error: {e}")
    except Exception as e:
        # Handle unexpected errors
        st.error(f"An unexpected error occurred: {e}")

else:
    st.info("Enter your project data in the sidebar and click 'Calculate Metrics' to see the evaluation.")


def get_decision_text(results: Dict[str, Any], rate: float) -> Tuple[str, bool]:
    """Provides a summary analysis based on the results."""
    npv = results.get('npv', 0)
    irr = results.get('irr', 0)
    pi = results.get('profitability_index', 0)

    decision_lines = []
    is_acceptable = False  # Default to not acceptable

    # Primary decision rule: NPV
    if npv > 0:
        decision_lines.append(
            f"• **NPV is positive (${npv:,.2f})**, which is the strongest signal to **ACCEPT** the project.")
        is_acceptable = True
    else:
        decision_lines.append(
            f"• **NPV is negative (${npv:,.2f})**, which is the strongest signal to **REJECT** the project.")
        is_acceptable = False

    # Secondary confirmation rules
    if isinstance(irr, float):
        if irr > rate:
            decision_lines.append(
                f"• IRR ({irr * 100:.2f}%) exceeds the discount rate ({rate * 100:.2f}%), confirming the positive NPV.")
        else:
            decision_lines.append(
                f"• IRR ({irr * 100:.2f}%) is below the discount rate ({rate * 100:.2f}%), confirming the negative NPV.")
    else:
        decision_lines.append(f"• IRR could not be calculated.")

    if isinstance(pi, float):
        if pi > 1:
            decision_lines.append(f"• Profitability Index ({pi:.3f}) is greater than 1, also suggesting acceptance.")
        else:
            decision_lines.append(f"• Profitability Index ({pi:.3f}) is not greater than 1, also suggesting rejection.")

    # Final Verdict
    if is_acceptable:
        verdict = "**Verdict: Based on the positive NPV and supporting metrics, this project appears to be a financially acceptable investment.**"
    else:
        verdict = "**Verdict: Based on the negative NPV and supporting metrics, this project is likely not a financially acceptable investment.**"

    decision_lines.append(f"\n{verdict}")
    return "\n".join(decision_lines), is_acceptable

