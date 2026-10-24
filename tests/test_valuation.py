"""Tests for deterministic valuation, INR formatting, milestones and weather alerts."""
import pytest

from modules import config as C
from modules import valuation as V
from modules import weather


def test_known_values_apartment_tier2_standard_half_done():
    r = V.compute_valuation("Residential Apartment", 1000, "Tier 2", 50, "Standard")
    assert r.total_budget == pytest.approx(1_800_000)
    assert r.capex_incurred == pytest.approx(900_000)
    assert r.market_value_full == pytest.approx(5_500_000)
    assert r.current_valuation == pytest.approx(5_500_000 * (0.30 + 0.70 * 0.5))
    assert r.cement_bags_total == pytest.approx(400)
    assert r.cement_bags_remaining == pytest.approx(200)
    assert r.steel_kg_total == pytest.approx(4000)
    assert r.steel_kg_remaining == pytest.approx(2000)
    assert r.milestone == "Superstructure"


def test_known_values_villa_tier1_premium():
    r = V.compute_valuation("Independent House/Villa", 2000, "Tier 1", 0, "Premium")
    assert r.total_budget == pytest.approx(2000 * 2200 * 1.25 * 1.3)
    assert r.capex_incurred == 0
    assert r.current_valuation == pytest.approx(2000 * 9500 * 1.15 * 0.30)


def test_full_completion_valuation_equals_market_value():
    r = V.compute_valuation("Commercial", 1500, "Tier 3", 100, "Basic")
    assert r.current_valuation == pytest.approx(r.market_value_full)
    assert r.capex_incurred == pytest.approx(r.total_budget)
    assert r.cement_bags_remaining == 0


def test_completion_is_clamped():
    high = V.compute_valuation("Industrial", 1000, "Tier 2", 150, "Standard")
    low = V.compute_valuation("Industrial", 1000, "Tier 2", -20, "Standard")
    assert high.completion == 100 and high.capex_incurred == pytest.approx(high.total_budget)
    assert low.completion == 0 and low.capex_incurred == 0


@pytest.mark.parametrize(
    "args",
    [
        ("Castle", 1000, "Tier 2", 10, "Standard"),
        ("Commercial", 1000, "Tier 9", 10, "Standard"),
        ("Commercial", 1000, "Tier 2", 10, "Gold"),
        ("Commercial", C.MIN_SQFT - 1, "Tier 2", 10, "Standard"),
        ("Commercial", C.MAX_SQFT + 1, "Tier 2", 10, "Standard"),
    ],
)
def test_invalid_inputs_raise(args):
    with pytest.raises(ValueError):
        V.compute_valuation(*args)


@pytest.mark.parametrize(
    "amount,expected",
    [
        (0, "₹0.00 Lakhs"),
        (99_999, "₹1.00 Lakhs"),
        (100_000, "₹1.00 Lakhs"),
        (2_160_000, "₹21.60 Lakhs"),
        (9_999_999, "₹1.00 Crores"),
        (10_000_000, "₹1.00 Crores"),
        (25_000_000, "₹2.50 Crores"),
        (-150_000, "-₹1.50 Lakhs"),
    ],
)
def test_format_inr_boundaries(amount, expected):
    assert V.format_inr(amount) == expected


@pytest.mark.parametrize(
    "completion,name",
    [
        (0, "Foundation"),
        (14.9, "Foundation"),
        (15, "Plinth"),
        (29.99, "Plinth"),
        (30, "Superstructure"),
        (59.9, "Superstructure"),
        (60, "Finishing"),
        (84.9, "Finishing"),
        (85, "Handover"),
        (100, "Handover"),
        (-5, "Foundation"),
        (150, "Handover"),
    ],
)
def test_milestone_mapping_edges(completion, name):
    assert V.milestone_for(completion) == name


def _statuses(completion):
    return [row["Status"] for row in V.milestone_table(completion)]


def test_milestone_table_statuses():
    assert _statuses(0) == ["In progress", "Pending", "Pending", "Pending", "Pending"]
    assert _statuses(40) == ["Done", "Done", "In progress", "Pending", "Pending"]
    assert _statuses(99) == ["Done", "Done", "Done", "Done", "In progress"]
    assert _statuses(100) == ["Done"] * 5


def test_weather_alerts_complete():
    assert weather.list_conditions() == ["High Wind", "Heavy Rain", "Extreme Heat", "Normal"]
    for condition in weather.list_conditions():
        alert = weather.get_alert(condition)
        assert alert["level"] in {"error", "warning", "success"}
        assert 4 <= len(alert["actions"]) <= 6
    wind = " ".join(weather.get_alert("High Wind")["actions"]).lower()
    assert "crane" in wind
    assert "electrical" in " ".join(weather.get_alert("Heavy Rain")["actions"]).lower()
    assert "curing" in " ".join(weather.get_alert("Extreme Heat")["actions"]).lower()


def test_weather_unknown_raises():
    with pytest.raises(ValueError):
        weather.get_alert("Tornado")
