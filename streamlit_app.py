import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import capital_budgeting_logic as logic
from typing import Dict, Any, Tuple
import io

# Set page configuration
st.set_page_config(
    layout="wide",
    page_title="Capital Budgeting Calculator",
    page_icon="💰"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .positive-metric {
        color: #28a745;
        font-weight: bold;
    }
    .negative-metric {
        color: #dc3545;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================================================
# HELPER FUNCTIONS - DEFINED AT THE TOP
# ============================================================================

def get_decision_text(results: Dict[str, Any], rate: float) -> Tuple[str, bool]:
    """Provides a summary analysis based on the results."""
    npv = results.get('npv', 0)
    irr = results.get('irr', 0)
    mirr = results.get('mirr', 0)
    pi = results.get('profitability_index', 0)

    decision_lines = []
    is_acceptable = False

    # Primary decision rule: NPV
    if npv > 0:
        decision_lines.append(
            f"• **NPV is positive (${npv:,.2f})**, which is the strongest signal to **ACCEPT** the project.")
        is_acceptable = True
    else:
        decision_lines.append(
            f"• **NPV is negative (${npv:,.2f})**, which is the strongest signal to **REJECT** the project.")
        is_acceptable = False

    # IRR analysis
    if isinstance(irr, float):
        if irr > rate:
            decision_lines.append(
                f"• IRR ({irr * 100:.2f}%) exceeds the discount rate ({rate * 100:.2f}%), confirming the positive NPV.")
        else:
            decision_lines.append(
                f"• IRR ({irr * 100:.2f}%) is below the discount rate ({rate * 100:.2f}%), confirming the negative NPV.")
    else:
        decision_lines.append(f"• IRR could not be calculated reliably for this project.")

    # MIRR analysis
    if isinstance(mirr, float):
        if mirr > rate:
            decision_lines.append(
                f"• MIRR ({mirr * 100:.2f}%) exceeds the discount rate, providing additional support.")
        else:
            decision_lines.append(
                f"• MIRR ({mirr * 100:.2f}%) is below the discount rate.")

    # PI analysis
    if isinstance(pi, float):
        if pi > 1:
            decision_lines.append(f"• Profitability Index ({pi:.3f}) is greater than 1, also suggesting acceptance.")
        else:
            decision_lines.append(f"• Profitability Index ({pi:.3f}) is not greater than 1, also suggesting rejection.")

    # Final Verdict
    if is_acceptable:
        verdict = "\n**✅ VERDICT: Based on the positive NPV and supporting metrics, this project appears to be a financially acceptable investment.**"
    else:
        verdict = "\n**❌ VERDICT: Based on the negative NPV and supporting metrics, this project is likely not a financially acceptable investment.**"

    decision_lines.append(verdict)
    return "\n\n".join(decision_lines), is_acceptable


# ============================================================================
# MAIN APPLICATION
# ============================================================================

# --- Initialize Session State ---
if 'calculated' not in st.session_state:
    st.session_state.calculated = False
if 'results' not in st.session_state:
    st.session_state.results = None
if 'inputs' not in st.session_state:
    st.session_state.inputs = None

# --- Main Title ---
st.markdown('<div class="main-header">💰 Capital Budgeting Calculator</div>', unsafe_allow_html=True)
st.markdown("### Comprehensive project evaluation with NPV, IRR, MIRR, and advanced analytics")

# --- Sidebar for Inputs ---
st.sidebar.header("📊 Project Inputs")

# Project Name
project_name = st.sidebar.text_input(
    "Project Name",
    value="New Investment Project",
    help="Give your project a name for identification"
)

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
    max_value=100.0,
    value=10.0,
    step=0.5,
    format="%.2f",
    help="Enter the weighted average cost of capital or required rate of return."
)

st.sidebar.markdown("---")
st.sidebar.subheader("Advanced Options (for MIRR)")

use_custom_rates = st.sidebar.checkbox(
    "Use custom reinvestment/finance rates",
    value=False,
    help="Check to specify different rates for MIRR calculation"
)

if use_custom_rates:
    reinvestment_rate = st.sidebar.number_input(
        "Reinvestment Rate (%)",
        min_value=0.0,
        max_value=100.0,
        value=discount_rate,
        step=0.5,
        format="%.2f",
        help="Rate for reinvesting positive cash flows"
    ) / 100.0

    finance_rate = st.sidebar.number_input(
        "Finance Rate (%)",
        min_value=0.0,
        max_value=100.0,
        value=discount_rate,
        step=0.5,
        format="%.2f",
        help="Rate for financing negative cash flows"
    ) / 100.0
else:
    reinvestment_rate = None
    finance_rate = None

st.sidebar.markdown("---")
st.sidebar.subheader("Cash Flow Input Method")

input_method = st.sidebar.radio(
    "Choose input method:",
    ["Manual Entry", "Upload CSV"],
    help="Enter cash flows manually or upload a CSV file"
)

future_cash_flows = []

if input_method == "Manual Entry":
    num_years = st.sidebar.number_input(
        "Number of Years",
        min_value=1,
        max_value=50,
        value=5,
        step=1,
        help="How many years of cash flows?"
    )

    st.sidebar.markdown("**Enter Cash Flows by Year:**")
    for i in range(num_years):
        cf = st.sidebar.number_input(
            f"Year {i + 1} ($)",
            value=25000.0 + (i * 5000.0),
            step=1000.0,
            format="%.2f",
            key=f"cf_{i}"
        )
        future_cash_flows.append(cf)

else:  # CSV Upload
    uploaded_file = st.sidebar.file_uploader(
        "Upload CSV with cash flows",
        type=['csv'],
        help="CSV should have 'Year' and 'CashFlow' columns"
    )

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            if 'CashFlow' in df.columns:
                future_cash_flows = df['CashFlow'].tolist()
                st.sidebar.success(f"✅ Loaded {len(future_cash_flows)} years of data")
            else:
                st.sidebar.error("CSV must have 'CashFlow' column")
        except Exception as e:
            st.sidebar.error(f"Error reading CSV: {e}")
    else:
        st.sidebar.info("Please upload a CSV file with cash flows")

# --- Calculate Button ---
calculate_button = st.sidebar.button("🚀 Calculate Metrics", type="primary", use_container_width=True)

if calculate_button and future_cash_flows:
    try:
        # Convert percentage to decimal
        rate = discount_rate / 100.0

        # Validate inputs
        if not future_cash_flows:
            raise ValueError("At least one Future Cash Flow is required.")

        # Calculate all metrics
        results = logic.calculate_all_metrics(
            rate,
            initial_investment,
            future_cash_flows,
            reinvestment_rate,
            finance_rate
        )

        # Store in session state
        st.session_state.calculated = True
        st.session_state.results = results
        st.session_state.inputs = {
            'project_name': project_name,
            'initial_investment': initial_investment,
            'discount_rate': discount_rate,
            'future_cash_flows': future_cash_flows,
            'rate': rate
        }

    except ValueError as e:
        st.error(f"❌ Input Error: {e}")
    except Exception as e:
        st.error(f"❌ An unexpected error occurred: {e}")

# --- Display Results ---
if st.session_state.calculated and st.session_state.results:
    results = st.session_state.results
    inputs = st.session_state.inputs

    # Create tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Summary",
        "📊 Visualizations",
        "🔍 Sensitivity Analysis",
        "📋 Detailed Report",
        "💾 Export"
    ])

    with tab1:
        st.header(f"Project: {inputs['project_name']}")

        # Key Metrics Row 1
        col1, col2, col3, col4 = st.columns(4)

        npv_val = results['npv']
        with col1:
            delta_color = "normal" if npv_val > 0 else "inverse"
            st.metric(
                label="Net Present Value (NPV)",
                value=f"${npv_val:,.2f}",
                delta="✓ Accept" if npv_val > 0 else "✗ Reject",
                delta_color=delta_color
            )

        irr_val = results['irr']
        with col2:
            if isinstance(irr_val, float):
                irr_text = f"{irr_val * 100:.2f}%"
                delta_text = f"{((irr_val - inputs['rate']) * 100):.2f}% vs WACC"
                delta_color = "normal" if irr_val > inputs['rate'] else "inverse"
            else:
                irr_text = "N/A"
                delta_text = None
                delta_color = "off"

            st.metric(
                label="Internal Rate of Return (IRR)",
                value=irr_text,
                delta=delta_text,
                delta_color=delta_color
            )

        mirr_val = results.get('mirr', 'N/A')
        with col3:
            if isinstance(mirr_val, float):
                mirr_text = f"{mirr_val * 100:.2f}%"
                delta_text = f"{((mirr_val - inputs['rate']) * 100):.2f}% vs WACC"
                delta_color = "normal" if mirr_val > inputs['rate'] else "inverse"
            else:
                mirr_text = "N/A"
                delta_text = None
                delta_color = "off"

            st.metric(
                label="Modified IRR (MIRR)",
                value=mirr_text,
                delta=delta_text,
                delta_color=delta_color
            )

        pi_val = results['profitability_index']
        with col4:
            if isinstance(pi_val, float):
                pi_text = f"{pi_val:.3f}"
                delta_text = "✓ Pass" if pi_val > 1 else "✗ Fail"
                delta_color = "normal" if pi_val > 1 else "inverse"
            else:
                pi_text = "N/A"
                delta_text = None
                delta_color = "off"

            st.metric(
                label="Profitability Index (PI)",
                value=pi_text,
                delta=delta_text,
                delta_color=delta_color
            )

        st.markdown("---")

        # Key Metrics Row 2
        col5, col6, col7, col8 = st.columns(4)

        with col5:
            pb_val = results['payback_period']
            st.metric(
                label="Payback Period",
                value=f"{pb_val} years" if isinstance(pb_val, float) else pb_val
            )

        with col6:
            dpb_val = results['discounted_payback_period']
            st.metric(
                label="Discounted Payback",
                value=f"{dpb_val} years" if isinstance(dpb_val, float) else dpb_val
            )

        with col7:
            eaa_val = results.get('eaa', 'N/A')
            if isinstance(eaa_val, float):
                st.metric(
                    label="Equivalent Annual Annuity",
                    value=f"${eaa_val:,.2f}"
                )
            else:
                st.metric(
                    label="Equivalent Annual Annuity",
                    value="N/A"
                )

        with col8:
            total_cf = results.get('total_cash_flow', 0)
            st.metric(
                label="Total Cash Flow",
                value=f"${total_cf:,.2f}",
                delta="Positive" if total_cf > 0 else "Negative",
                delta_color="normal" if total_cf > 0 else "inverse"
            )

        st.markdown("---")

        # Decision Analysis
        st.subheader("🎯 Decision Analysis")
        decision_text, is_acceptable = get_decision_text(results, inputs['rate'])

        if is_acceptable:
            st.success(decision_text)
        else:
            st.error(decision_text)

    with tab2:
        st.header("📊 Visual Analytics")

        # Cash Flow Timeline
        years = list(range(len(inputs['future_cash_flows']) + 1))
        cash_flows_with_initial = [-inputs['initial_investment']] + inputs['future_cash_flows']

        fig1 = go.Figure()
        colors = ['red' if cf < 0 else 'green' for cf in cash_flows_with_initial]

        fig1.add_trace(go.Bar(
            x=years,
            y=cash_flows_with_initial,
            marker_color=colors,
            text=[f"${cf:,.0f}" for cf in cash_flows_with_initial],
            textposition='outside',
            name='Cash Flow'
        ))

        fig1.update_layout(
            title="Cash Flow Timeline",
            xaxis_title="Year",
            yaxis_title="Cash Flow ($)",
            showlegend=False,
            height=400,
            hovermode='x unified'
        )

        st.plotly_chart(fig1, use_container_width=True)

        # Cumulative Cash Flow (Payback Visualization)
        years_cum, cum_undiscounted, cum_discounted = logic.calculate_cumulative_cash_flows(
            inputs['initial_investment'],
            inputs['future_cash_flows'],
            inputs['rate']
        )

        fig2 = go.Figure()

        fig2.add_trace(go.Scatter(
            x=years_cum,
            y=cum_undiscounted,
            mode='lines+markers',
            name='Cumulative (Undiscounted)',
            line=dict(color='blue', width=2)
        ))

        fig2.add_trace(go.Scatter(
            x=years_cum,
            y=cum_discounted,
            mode='lines+markers',
            name='Cumulative (Discounted)',
            line=dict(color='orange', width=2)
        ))

        fig2.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Break-even")

        fig2.update_layout(
            title="Cumulative Cash Flow (Payback Analysis)",
            xaxis_title="Year",
            yaxis_title="Cumulative Cash Flow ($)",
            height=400,
            hovermode='x unified'
        )

        st.plotly_chart(fig2, use_container_width=True)

        # NPV Profile
        rates, npvs = logic.calculate_npv_profile(
            inputs['initial_investment'],
            inputs['future_cash_flows']
        )

        fig3 = go.Figure()

        fig3.add_trace(go.Scatter(
            x=[r * 100 for r in rates],
            y=npvs,
            mode='lines',
            name='NPV',
            line=dict(color='purple', width=3),
            fill='tozeroy'
        ))

        fig3.add_vline(
            x=inputs['discount_rate'],
            line_dash="dash",
            line_color="green",
            annotation_text=f"Current WACC: {inputs['discount_rate']:.1f}%"
        )

        fig3.add_hline(y=0, line_dash="dash", line_color="red")

        # Mark IRR if available
        if isinstance(results['irr'], float):
            fig3.add_vline(
                x=results['irr'] * 100,
                line_dash="dot",
                line_color="blue",
                annotation_text=f"IRR: {results['irr'] * 100:.1f}%"
            )

        fig3.update_layout(
            title="NPV Profile (NPV at Different Discount Rates)",
            xaxis_title="Discount Rate (%)",
            yaxis_title="Net Present Value ($)",
            height=400,
            hovermode='x unified'
        )

        st.plotly_chart(fig3, use_container_width=True)

    with tab3:
        st.header("🔍 Sensitivity Analysis")
        st.markdown("Analyze how changes in key inputs affect NPV")

        variation_pct = st.slider(
            "Variation Percentage",
            min_value=5,
            max_value=50,
            value=20,
            step=5,
            help="Test ±X% changes in inputs"
        )

        sensitivity_results = logic.perform_sensitivity_analysis(
            inputs['initial_investment'],
            inputs['future_cash_flows'],
            inputs['rate'],
            variation_pct
        )

        # Create sensitivity table
        sensitivity_data = []
        for variable, values in sensitivity_results.items():
            sensitivity_data.append({
                'Variable': variable.replace('_', ' ').title(),
                f'-{variation_pct}%': f"${values['low']:,.2f}",
                'Base Case': f"${values['base']:,.2f}",
                f'+{variation_pct}%': f"${values['high']:,.2f}",
                'Range': f"${values['high'] - values['low']:,.2f}"
            })

        df_sensitivity = pd.DataFrame(sensitivity_data)
        st.dataframe(df_sensitivity, use_container_width=True)

        # Tornado chart
        tornado_data = []
        for variable, values in sensitivity_results.items():
            impact_negative = values['low'] - values['base']
            impact_positive = values['high'] - values['base']
            tornado_data.append({
                'Variable': variable.replace('_', ' ').title(),
                'Negative Impact': impact_negative,
                'Positive Impact': impact_positive,
                'Total Range': abs(impact_positive - impact_negative)
            })

        df_tornado = pd.DataFrame(tornado_data).sort_values('Total Range', ascending=True)

        fig4 = go.Figure()

        fig4.add_trace(go.Bar(
            y=df_tornado['Variable'],
            x=df_tornado['Negative Impact'],
            name=f'-{variation_pct}%',
            orientation='h',
            marker_color='red'
        ))

        fig4.add_trace(go.Bar(
            y=df_tornado['Variable'],
            x=df_tornado['Positive Impact'],
            name=f'+{variation_pct}%',
            orientation='h',
            marker_color='green'
        ))

        fig4.update_layout(
            title="Tornado Chart - NPV Sensitivity",
            xaxis_title="Change in NPV ($)",
            yaxis_title="Variable",
            barmode='relative',
            height=400
        )

        st.plotly_chart(fig4, use_container_width=True)

    with tab4:
        st.header("📋 Detailed Project Report")

        # Project Summary
        st.subheader("Project Information")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"""
            **Project Name:** {inputs['project_name']}  
            **Initial Investment:** ${inputs['initial_investment']:,.2f}  
            **Discount Rate (WACC):** {inputs['discount_rate']:.2f}%  
            **Project Duration:** {len(inputs['future_cash_flows'])} years
            """)

        with col2:
            avg_cf = results.get('avg_annual_cash_flow', 0)
            st.markdown(f"""
            **Average Annual Cash Flow:** ${avg_cf:,.2f}  
            **Total Undiscounted Cash Flow:** ${results.get('total_cash_flow', 0):,.2f}  
            **Net Present Value:** ${results['npv']:,.2f}
            """)

        # Cash Flow Table
        st.subheader("Cash Flow Schedule")
        cf_data = []
        cumulative = -inputs['initial_investment']
        discounted_cumulative = -inputs['initial_investment']

        cf_data.append({
            'Year': 0,
            'Cash Flow': f"-${inputs['initial_investment']:,.2f}",
            'Discounted CF': f"-${inputs['initial_investment']:,.2f}",
            'Cumulative CF': f"-${inputs['initial_investment']:,.2f}",
            'Cumulative Discounted CF': f"-${inputs['initial_investment']:,.2f}"
        })

        for i, cf in enumerate(inputs['future_cash_flows']):
            year = i + 1
            discounted_cf = cf / ((1 + inputs['rate']) ** year)
            cumulative += cf
            discounted_cumulative += discounted_cf

            cf_data.append({
                'Year': year,
                'Cash Flow': f"${cf:,.2f}",
                'Discounted CF': f"${discounted_cf:,.2f}",
                'Cumulative CF': f"${cumulative:,.2f}",
                'Cumulative Discounted CF': f"${discounted_cumulative:,.2f}"
            })

        df_cf = pd.DataFrame(cf_data)
        st.dataframe(df_cf, use_container_width=True)

        # All Metrics Summary
        st.subheader("Complete Metrics Summary")

        metrics_display = {
            'Net Present Value (NPV)': f"${results['npv']:,.2f}",
            'Internal Rate of Return (IRR)': f"{results['irr'] * 100:.2f}%" if isinstance(results['irr'], float) else
            results['irr'],
            'Modified IRR (MIRR)': f"{results['mirr'] * 100:.2f}%" if isinstance(results['mirr'], float) else results[
                'mirr'],
            'Profitability Index (PI)': f"{results['profitability_index']:.3f}" if isinstance(
                results['profitability_index'], float) else results['profitability_index'],
            'Payback Period': f"{results['payback_period']} years" if isinstance(results['payback_period'], float) else
            results['payback_period'],
            'Discounted Payback Period': f"{results['discounted_payback_period']} years" if isinstance(
                results['discounted_payback_period'], float) else results['discounted_payback_period'],
            'Equivalent Annual Annuity (EAA)': f"${results['eaa']:,.2f}" if isinstance(results['eaa'], float) else
            results['eaa'],
            'Benefit-Cost Ratio': f"{results.get('benefit_cost_ratio', 'N/A'):.3f}" if isinstance(
                results.get('benefit_cost_ratio'), float) else results.get('benefit_cost_ratio', 'N/A'),
            'Total Cash Flow': f"${results.get('total_cash_flow', 0):,.2f}",
            'Average Annual Cash Flow': f"${results.get('avg_annual_cash_flow', 0):,.2f}"
        }

        df_metrics = pd.DataFrame(list(metrics_display.items()), columns=['Metric', 'Value'])
        st.dataframe(df_metrics, use_container_width=True)

    with tab5:
        st.header("💾 Export Results")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Export to CSV")

            # Prepare data for CSV
            export_data = {
                'Metric': list(metrics_display.keys()),
                'Value': list(metrics_display.values())
            }
            df_export = pd.DataFrame(export_data)

            csv = df_export.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"{inputs['project_name']}_analysis.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col2:
            st.subheader("Export Cash Flows")

            csv_cf = df_cf.to_csv(index=False)
            st.download_button(
                label="📥 Download Cash Flow Schedule",
                data=csv_cf,
                file_name=f"{inputs['project_name']}_cashflows.csv",
                mime="text/csv",
                use_container_width=True
            )

        # Print-friendly summary
        st.subheader("📄 Print-Friendly Summary")

        decision_text, is_acceptable = get_decision_text(results, inputs['rate'])

        summary_text = f"""
# Capital Budgeting Analysis Report
## Project: {inputs['project_name']}

### Project Parameters
- Initial Investment: ${inputs['initial_investment']:,.2f}
- Discount Rate (WACC): {inputs['discount_rate']:.2f}%
- Project Duration: {len(inputs['future_cash_flows'])} years

### Key Financial Metrics
- **Net Present Value (NPV):** ${results['npv']:,.2f}
- **Internal Rate of Return (IRR):** {f"{results['irr'] * 100:.2f}%" if isinstance(results['irr'], float) else results['irr']}
- **Modified IRR (MIRR):** {f"{results['mirr'] * 100:.2f}%" if isinstance(results['mirr'], float) else results['mirr']}
- **Profitability Index (PI):** {f"{results['profitability_index']:.3f}" if isinstance(results['profitability_index'], float) else results['profitability_index']}
- **Payback Period:** {f"{results['payback_period']} years" if isinstance(results['payback_period'], float) else results['payback_period']}
- **Discounted Payback Period:** {f"{results['discounted_payback_period']} years" if isinstance(results['discounted_payback_period'], float) else results['discounted_payback_period']}

### Recommendation
{decision_text}

---
Report generated on: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        st.text_area("Copy this report:", summary_text, height=400)

        st.download_button(
            label="📥 Download Report (TXT)",
            data=summary_text,
            file_name=f"{inputs['project_name']}_report.txt",
            mime="text/plain",
            use_container_width=True
        )

else:
    # Welcome screen
    st.info("👈 Enter your project data in the sidebar and click '🚀 Calculate Metrics' to begin the analysis.")

    # Show example/tutorial
    with st.expander("📚 How to Use This Calculator"):
        st.markdown("""
        ### Getting Started

        1. **Enter Basic Information:**
           - Project name for identification
           - Initial investment amount (Year 0 cost)
           - Discount rate (WACC or required return rate)

        2. **Input Cash Flows:**
           - Choose manual entry or CSV upload
           - Enter expected cash flows for each year
           - Positive values = cash inflows, Negative values = cash outflows

        3. **Advanced Options (Optional):**
           - Customize reinvestment and finance rates for MIRR calculation

        4. **Click Calculate:**
           - Review comprehensive metrics across multiple tabs
           - Visualize cash flows and NPV profiles
           - Perform sensitivity analysis
           - Export results

        ### Key Metrics Explained

        - **NPV (Net Present Value):** Positive NPV = Accept, Negative NPV = Reject
        - **IRR (Internal Rate of Return):** Compare to discount rate; higher is better
        - **MIRR (Modified IRR):** More realistic than IRR for projects with multiple sign changes
        - **PI (Profitability Index):** Should be > 1 for acceptance
        - **Payback Period:** Time to recover initial investment
        - **EAA (Equivalent Annual Annuity):** Useful for comparing projects of different durations
        """)

    # Sample data button
    if st.button("📋 Load Sample Project"):
        st.session_state.sample_loaded = True
        st.rerun()



