"""Deterministic project budget, valuation, materials and milestone logic (INR)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from . import config as C

LAKH = 100_000
CRORE = 10_000_000


def format_inr(amount: float) -> str:
    """Format an INR amount as Lakhs (< 1 Crore) or Crores (>= 1 Crore)."""
    if amount < 0:
        return "-" + format_inr(-amount)
    lakhs = amount / LAKH
    if amount >= CRORE or round(lakhs, 2) >= 100:
        return f"₹{amount / CRORE:.2f} Crores"
    return f"₹{lakhs:.2f} Lakhs"


def clamp_completion(completion: float) -> float:
    """Clamp completion percentage into [0, 100]."""
    return max(0.0, min(100.0, float(completion)))


def milestone_for(completion: float) -> str:
    """Return the name of the current milestone for a completion percentage."""
    c = clamp_completion(completion)
    for name, start, end in C.MILESTONES:
        if start <= c < end:
            return name
    return C.MILESTONES[-1][0]


def milestone_table(completion: float) -> List[Dict[str, str]]:
    """Return milestone rows with Done / In progress / Pending status."""
    c = clamp_completion(completion)
    rows: List[Dict[str, str]] = []
    last = len(C.MILESTONES) - 1
    for i, (name, start, end) in enumerate(C.MILESTONES):
        if c >= end and (i != last or c >= 100):
            status = "Done"
        elif c >= start:
            status = "In progress"
        else:
            status = "Pending"
        rows.append({"Milestone": name, "Range": f"{start}-{end}%", "Status": status})
    return rows


@dataclass(frozen=True)
class ValuationResult:
    """All outputs of the planning & valuation calculation."""

    total_budget: float
    capex_incurred: float
    market_value_full: float
    current_valuation: float
    cement_bags_total: float
    cement_bags_remaining: float
    steel_kg_total: float
    steel_kg_remaining: float
    completion: float
    milestone: str


def compute_valuation(
    structure: str, sqft: float, tier: str, completion: float, finish: str
) -> ValuationResult:
    """Compute budget, capex, valuation and material needs.

    Raises:
        ValueError: if any input is unknown or ``sqft`` is outside the allowed range.
    """
    if structure not in C.BASE_CONSTRUCTION_RATE:
        raise ValueError(f"Unknown structure type: {structure}")
    if tier not in C.TIER_COST_MULTIPLIER:
        raise ValueError(f"Unknown location tier: {tier}")
    if finish not in C.FINISH_MULTIPLIER:
        raise ValueError(f"Unknown finish level: {finish}")
    if not (C.MIN_SQFT <= sqft <= C.MAX_SQFT):
        raise ValueError(f"Built-up area must be between {C.MIN_SQFT} and {C.MAX_SQFT} sqft")

    c = clamp_completion(completion)
    total_budget = (
        sqft
        * C.BASE_CONSTRUCTION_RATE[structure]
        * C.TIER_COST_MULTIPLIER[tier]
        * C.FINISH_MULTIPLIER[finish]
    )
    capex = total_budget * c / 100
    market_full = sqft * C.MARKET_RATE_PER_SQFT[tier] * C.STRUCTURE_MARKET_MULTIPLIER[structure]
    current_val = market_full * (C.LAND_VALUE_SHARE + (1 - C.LAND_VALUE_SHARE) * c / 100)
    cement_total = sqft * C.CEMENT_BAGS_PER_SQFT
    steel_total = sqft * C.STEEL_KG_PER_SQFT
    remaining = 1 - c / 100
    return ValuationResult(
        total_budget=total_budget,
        capex_incurred=capex,
        market_value_full=market_full,
        current_valuation=current_val,
        cement_bags_total=cement_total,
        cement_bags_remaining=cement_total * remaining,
        steel_kg_total=steel_total,
        steel_kg_remaining=steel_total * remaining,
        completion=c,
        milestone=milestone_for(c),
    )
