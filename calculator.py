"""
Pure commission calculation engine — no database imports, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class BracketRow:
    upper_bound: Optional[float]  # None = infinity
    rate: float
    sort_order: int


@dataclass
class CollectionInput:
    id: int
    project_id: int
    project_no: Optional[str]
    customer: Optional[str]
    collection_amount: float
    collection_date: object        # datetime.date or None
    sales_tax: float
    referral_fee: float
    approved_sales_exp: float
    distribution: float            # this employee's share of the project (0.0–1.0)


@dataclass
class StatementRow:
    # Pass-through
    id: int
    project_id: int
    project_no: Optional[str]
    customer: Optional[str]
    collection_amount: float
    collection_date: object
    distribution: float

    # Computed
    net_revenue: float              # collection_amount - tax - referral - exp
    employee_net_revenue: float     # net_revenue * distribution
    calc_revenue_accumulated: float # running sum of employee_net_revenue
    commission_earned: float        # incremental commission this row
    commission_accumulated: float   # running total earned
    commission_payable: float       # 0 if still below threshold
    commission_due: float           # commission_accumulated - total_payments


def _sorted_brackets(brackets: list[BracketRow]) -> list[BracketRow]:
    return sorted(brackets, key=lambda b: (b.upper_bound is None, b.upper_bound or 0))


def _marginal_commission(
    prev_acc: float,
    new_acc: float,
    brackets: list[BracketRow],
    threshold: float,
) -> float:
    """
    Commission earned on the revenue band [prev_acc, new_acc].
    Revenue below `threshold` earns 0%.
    """
    if new_acc <= prev_acc:
        return 0.0

    total = 0.0
    lower = prev_acc

    for bracket in _sorted_brackets(brackets):
        upper = bracket.upper_bound if bracket.upper_bound is not None else float("inf")
        if lower >= upper:
            continue
        band_start = max(lower, 0.0)
        band_end = min(new_acc, upper)
        if band_start >= band_end:
            continue

        taxable_start = max(band_start, threshold)
        if taxable_start < band_end:
            total += (band_end - taxable_start) * bracket.rate

        lower = upper
        if lower >= new_acc:
            break

    return round(total, 2)


def compute_employee_statement(
    collections: list[CollectionInput],
    brackets: list[BracketRow],
    commission_threshold: float,
    total_payments: float = 0.0,
) -> list[StatementRow]:
    """
    Compute a commission statement for one employee across all their projects.

    `collections` must be pre-sorted by collection_date, id.
    `total_payments` is the sum of all EmployeePayment.amount for this employee/cycle.
    """
    accumulated_revenue = 0.0
    accumulated_earned = 0.0
    rows: list[StatementRow] = []

    for col in collections:
        net_rev = (
            col.collection_amount
            - col.sales_tax
            - col.referral_fee
            - col.approved_sales_exp
        )
        emp_net = net_rev * col.distribution
        prev_acc = accumulated_revenue
        accumulated_revenue += emp_net

        # Retroactive catch-up when threshold is first crossed
        if prev_acc < commission_threshold <= accumulated_revenue:
            full = _marginal_commission(0, accumulated_revenue, brackets, 0.0)
            already = _marginal_commission(0, prev_acc, brackets, 0.0)
            earned = round(full - already, 2)
        else:
            earned = _marginal_commission(prev_acc, accumulated_revenue, brackets, commission_threshold)

        accumulated_earned += earned

        commission_payable = earned if accumulated_revenue > commission_threshold else 0.0
        commission_due = round(accumulated_earned - total_payments, 2)

        rows.append(StatementRow(
            id=col.id,
            project_id=col.project_id,
            project_no=col.project_no,
            customer=col.customer,
            collection_amount=col.collection_amount,
            collection_date=col.collection_date,
            distribution=col.distribution,
            net_revenue=round(net_rev, 2),
            employee_net_revenue=round(emp_net, 2),
            calc_revenue_accumulated=round(accumulated_revenue, 2),
            commission_earned=earned,
            commission_accumulated=round(accumulated_earned, 2),
            commission_payable=round(commission_payable, 2),
            commission_due=commission_due,
        ))

    return rows
