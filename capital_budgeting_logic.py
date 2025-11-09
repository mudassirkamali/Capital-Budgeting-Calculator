import numpy as np
import numpy_financial as npf
from typing import List, Dict, Union, Optional, Tuple


def calculate_all_metrics(
        rate: float,
        initial_investment_positive: float,
        future_cash_flows: List[float],
        reinvestment_rate: Optional[float] = None,
        finance_rate: Optional[float] = None
) -> Dict[str, Union[float, str]]:
    """
    Calculates all key capital budgeting metrics.

    Args:
        rate: The discount rate (e.g., 0.1 for 10%).
        initial_investment_positive: The initial cost, as a positive number.
        future_cash_flows: A list of cash flows for years 1, 2, ...
        reinvestment_rate: Rate for reinvesting positive cash flows (for MIRR). Defaults to 'rate'.
        finance_rate: Rate for financing negative cash flows (for MIRR). Defaults to 'rate'.

    Returns:
        A dictionary containing all calculated metrics.
    """

    # --- Input Validation ---
    if not future_cash_flows:
        raise ValueError("No future cash flows provided.")
    if initial_investment_positive <= 0:
        raise ValueError("Initial investment must be a positive number.")
    if rate <= -1:
        raise ValueError("Discount rate cannot be -100% or less.")

    # Set default rates for MIRR if not provided
    if reinvestment_rate is None:
        reinvestment_rate = rate
    if finance_rate is None:
        finance_rate = rate

    initial_investment_negative = -initial_investment_positive
    results = {}

    # --- 1. Net Present Value (NPV) ---
    pv_future_flows = npf.npv(rate, future_cash_flows)
    results['npv'] = pv_future_flows + initial_investment_negative

    # --- 2. Internal Rate of Return (IRR) ---
    all_cash_flows = [initial_investment_negative] + future_cash_flows
    try:
        irr_value = npf.irr(all_cash_flows)
        # Check if IRR is a valid number
        if np.isnan(irr_value) or np.isinf(irr_value):
            results['irr'] = "N/A (No Valid Solution)"
        else:
            results['irr'] = irr_value
    except (ValueError, RuntimeError):
        results['irr'] = "N/A (Calculation Error)"

    # --- 3. Modified Internal Rate of Return (MIRR) ---
    try:
        mirr_value = npf.mirr(all_cash_flows, finance_rate, reinvestment_rate)
        if np.isnan(mirr_value) or np.isinf(mirr_value):
            results['mirr'] = "N/A (No Valid Solution)"
        else:
            results['mirr'] = mirr_value
    except (ValueError, RuntimeError):
        results['mirr'] = "N/A (Calculation Error)"

    # --- 4. Payback Period ---
    results['payback_period'] = _calculate_payback(
        initial_investment_positive, future_cash_flows
    )

    # --- 5. Discounted Payback Period ---
    results['discounted_payback_period'] = _calculate_discounted_payback(
        rate, initial_investment_positive, future_cash_flows
    )

    # --- 6. Profitability Index (PI) ---
    if initial_investment_positive == 0:
        results['profitability_index'] = "N/A (No Investment)"
    else:
        results['profitability_index'] = pv_future_flows / initial_investment_positive

    # --- 7. Equivalent Annual Annuity (EAA) ---
    n_years = len(future_cash_flows)
    if results['npv'] != 0 and n_years > 0:
        try:
            # EAA = NPV / Present Value Annuity Factor
            pv_annuity_factor = (1 - (1 + rate) ** -n_years) / rate if rate != 0 else n_years
            results['eaa'] = results['npv'] / pv_annuity_factor
        except (ZeroDivisionError, ValueError):
            results['eaa'] = "N/A (Calculation Error)"
    else:
        results['eaa'] = "N/A"

    # --- 8. Benefit-Cost Ratio (BCR) ---
    if initial_investment_positive > 0:
        results['benefit_cost_ratio'] = pv_future_flows / initial_investment_positive
    else:
        results['benefit_cost_ratio'] = "N/A"

    # --- 9. Total Cash Flow ---
    results['total_cash_flow'] = sum(future_cash_flows) - initial_investment_positive

    # --- 10. Average Annual Cash Flow ---
    results['avg_annual_cash_flow'] = sum(future_cash_flows) / len(future_cash_flows)

    return results


def _calculate_payback(investment: float, cash_flows: List[float]) -> Union[float, str]:
    """Calculates the simple payback period."""
    cumulative_cash_flow = 0.0
    for i, cash_flow in enumerate(cash_flows):
        year = i + 1
        cumulative_cash_flow += cash_flow

        if cumulative_cash_flow >= investment:
            # Calculate exact payback with fractional year
            last_year_cumulative = cumulative_cash_flow - cash_flow
            needed_from_this_year = investment - last_year_cumulative

            if cash_flow <= 0:
                continue

            payback = (year - 1) + (needed_from_this_year / cash_flow)
            return round(payback, 2)

    return "Never"


def _calculate_discounted_payback(rate: float, investment: float, cash_flows: List[float]) -> Union[float, str]:
    """Calculates the discounted payback period."""
    cumulative_discounted_cash_flow = 0.0
    for i, cash_flow in enumerate(cash_flows):
        year = i + 1
        discounted_cf = cash_flow / ((1 + rate) ** year)
        cumulative_discounted_cash_flow += discounted_cf

        if cumulative_discounted_cash_flow >= investment:
            last_year_cumulative_discounted = cumulative_discounted_cash_flow - discounted_cf
            needed_from_this_year = investment - last_year_cumulative_discounted

            if discounted_cf <= 0:
                continue

            discounted_payback = (year - 1) + (needed_from_this_year / discounted_cf)
            return round(discounted_payback, 2)

    return "Never"


def calculate_npv_profile(
        initial_investment_positive: float,
        future_cash_flows: List[float],
        rate_range: Tuple[float, float] = (0, 0.50),
        num_points: int = 50
) -> Tuple[List[float], List[float]]:
    """
    Calculates NPV at different discount rates for NPV profile chart.

    Args:
        initial_investment_positive: Initial investment as positive number
        future_cash_flows: List of future cash flows
        rate_range: Tuple of (min_rate, max_rate) for analysis
        num_points: Number of points to calculate

    Returns:
        Tuple of (rates, npvs) lists
    """
    rates = np.linspace(rate_range[0], rate_range[1], num_points)
    npvs = []

    initial_investment_negative = -initial_investment_positive

    for rate in rates:
        pv_future_flows = npf.npv(rate, future_cash_flows)
        npv = pv_future_flows + initial_investment_negative
        npvs.append(npv)

    return rates.tolist(), npvs


def calculate_cumulative_cash_flows(
        initial_investment_positive: float,
        future_cash_flows: List[float],
        rate: float
) -> Tuple[List[int], List[float], List[float]]:
    """
    Calculates cumulative cash flows for payback visualization.

    Returns:
        Tuple of (years, cumulative_undiscounted, cumulative_discounted)
    """
    years = [0] + list(range(1, len(future_cash_flows) + 1))
    cumulative_undiscounted = [-initial_investment_positive]
    cumulative_discounted = [-initial_investment_positive]

    for i, cf in enumerate(future_cash_flows):
        year = i + 1
        # Undiscounted cumulative
        cumulative_undiscounted.append(cumulative_undiscounted[-1] + cf)

        # Discounted cumulative
        discounted_cf = cf / ((1 + rate) ** year)
        cumulative_discounted.append(cumulative_discounted[-1] + discounted_cf)

    return years, cumulative_undiscounted, cumulative_discounted


def perform_sensitivity_analysis(
        initial_investment_positive: float,
        future_cash_flows: List[float],
        base_rate: float,
        variation_percent: float = 20.0
) -> Dict[str, Dict[str, float]]:
    """
    Performs sensitivity analysis on NPV by varying inputs.

    Args:
        initial_investment_positive: Base initial investment
        future_cash_flows: Base cash flows
        base_rate: Base discount rate
        variation_percent: Percentage variation to test (e.g., 20 for ±20%)

    Returns:
        Dictionary with sensitivity results
    """
    variation = variation_percent / 100.0
    results = {}

    # Discount rate sensitivity
    rates = [
        base_rate * (1 - variation),
        base_rate,
        base_rate * (1 + variation)
    ]
    rate_npvs = []
    for r in rates:
        pv = npf.npv(r, future_cash_flows)
        npv = pv - initial_investment_positive
        rate_npvs.append(npv)

    results['discount_rate'] = {
        'low': rate_npvs[0],
        'base': rate_npvs[1],
        'high': rate_npvs[2]
    }

    # Cash flow sensitivity
    cf_variations = [
        [cf * (1 - variation) for cf in future_cash_flows],
        future_cash_flows,
        [cf * (1 + variation) for cf in future_cash_flows]
    ]
    cf_npvs = []
    for cfs in cf_variations:
        pv = npf.npv(base_rate, cfs)
        npv = pv - initial_investment_positive
        cf_npvs.append(npv)

    results['cash_flows'] = {
        'low': cf_npvs[0],
        'base': cf_npvs[1],
        'high': cf_npvs[2]
    }

    # Initial investment sensitivity
    inv_variations = [
        initial_investment_positive * (1 - variation),
        initial_investment_positive,
        initial_investment_positive * (1 + variation)
    ]
    inv_npvs = []
    pv = npf.npv(base_rate, future_cash_flows)
    for inv in inv_variations:
        npv = pv - inv
        inv_npvs.append(npv)

    results['initial_investment'] = {
        'low': inv_npvs[0],
        'base': inv_npvs[1],
        'high': inv_npvs[2]
    }

    return results
