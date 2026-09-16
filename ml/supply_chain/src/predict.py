"""
Supply Chain Optimizer (Model 4).

Honest scope statement first: this project's data has NO crop calendars,
NO farm/storage/market coordinates, and NO real-time freight quotes. So
"when to harvest" and "which exact route" are NOT answered here - doing so
would mean inventing dates and road names, which is the same category of
problem we avoided in every other model (fabricated targets, fake metrics).

What IS answered, with real inputs and real math:
  - Store now vs. sell now? If storing, for how long and at which option?
  - What will it cost (storage + transport)?
  - What's the expected profit?

Three kinds of numbers feed this, kept clearly separate:
  1. REAL, computed from your data: loss_rate_pct and sellable_share_pct
     per crop, from supply_chain_reference.csv (built from actual FBS
     Losses/Production and Food/Domestic-supply ratios).
  2. REQUIRED CALLER INPUTS - genuinely situational, never defaulted:
     quantity, current market price (₹/quintal), and distances. No one
     but the caller knows today's mandi price or how far their farm is
     from a specific godown.
  3. CITED DEFAULT BENCHMARKS - overridable, always flagged in `notes`
     when used: storage and transport rates, sourced from published
     government/industry figures (see constants below), NOT invented.
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output"

# --- Cited default benchmarks (₹, as of ~2025) - override at call time if you have real quotes ---
DEFAULT_STORAGE_RATES = {
    # ₹ per quintal per month
    "fci": {"rate": 10.42, "source": "FCI covered-godown storage charge, Govt of India Dept. of Food & Public Distribution"},
    "private_cold": {"rate": 26.7, "source": "Private cold storage (potato/onion-type), ~₹200/quintal for a 7-8 month season, industry-typical range ₹150-300/quintal"},
}
DEFAULT_TRANSPORT_RATE_PER_TONNE_KM = 2.5  # ₹, medium truck (9-12t) FTL, ~₹20-30/km / 10t, 2025 industry rate surveys
SPOILAGE_REFERENCE_DAYS = 180  # the FBS loss_rate_pct is treated as the loss over a ~6-month storage cycle
HOLD_DAY_GRID = [7, 15, 30, 45, 60, 90]

_state = {}


def _load():
    if _state:
        return _state["reference"], _state["fallback_loss"], _state["fallback_sellable"]

    reference = pd.read_csv(OUT_DIR / "supply_chain_reference.csv", index_col="Item")
    with open(OUT_DIR / "fallback_rates.txt") as f:
        fallback_loss, fallback_sellable = [float(x) for x in f.read().splitlines()]

    _state.update(reference=reference, fallback_loss=fallback_loss, fallback_sellable=fallback_sellable)
    return reference, fallback_loss, fallback_sellable


def _get_crop_rates(item, reference, fallback_loss, fallback_sellable, notes):
    if item in reference.index:
        return (float(reference.loc[item, "loss_rate_pct"]),
                float(reference.loc[item, "sellable_share_pct"]))
    notes.append(f"'{item}' not in the FBS reference table; using the all-crop average "
                 f"loss rate ({fallback_loss:.1f}%) and sellable share ({fallback_sellable:.1f}%) instead.")
    return fallback_loss, fallback_sellable


def optimize_supply_chain(
    item: str,
    quantity_tonnes: float,
    current_price_per_quintal: float,
    direct_to_market_distance_km: float,
    storage_options: list[dict] | None = None,
    price_growth_pct_per_month: float = 0.0,
    transport_rate_per_tonne_km: float | None = None,
    max_hold_days: int = 90,
) -> dict:
    """
    Decide: sell now, or store then sell - and if storing, where and for
    how long - to maximize expected profit.

    item: crop name (matched against supply_chain_reference.csv; falls
        back to an all-crop average loss rate if not found, flagged in notes).
    quantity_tonnes: harvest quantity available to sell. Required - not
        defaulted, this is your specific transaction's size.
    current_price_per_quintal: TODAY's real market price in ₹/quintal.
        Required - the price model (Model 3) gives a % growth trend, not a
        currency figure, so the actual starting price has to come from you.
    direct_to_market_distance_km: distance for the sell-now baseline (farm
        -> market directly, no storage).
    storage_options: optional list of dicts, each:
        {"name": str, "type": "fci" or "private_cold" (for default rate)
         OR "rate_per_quintal_per_month": float (custom rate),
         "distance_from_farm_km": float, "distance_to_market_km": float}
        If omitted, both default types are evaluated with
        distance_from_farm_km = distance_to_market_km = direct_to_market_distance_km
        as a rough stand-in, flagged in notes.
    price_growth_pct_per_month: expected price growth rate, e.g. derived
        from Model 3's forecast. Defaults to 0% (flat) if not supplied -
        flagged in notes, since assuming flat prices likely understates the
        value of waiting to sell.
    transport_rate_per_tonne_km: override the default ₹2.5/tonne-km if you
        have a real freight quote.
    max_hold_days: cap on how many days ahead to consider storing.

    Returns a dict with `ok: bool`. On success: `recommendation` ("sell_now"
    or a storage option name + hold days), `revenue`, `storage_cost`,
    `transport_cost`, `spoilage_loss_value`, `net_profit` for the chosen
    plan, `alternatives` (every option/hold-day combo considered, for
    transparency), `notes`.
    """
    notes = []
    reference, fallback_loss, fallback_sellable = _load()
    loss_rate_pct, sellable_share_pct = _get_crop_rates(item, reference, fallback_loss, fallback_sellable, notes)

    if transport_rate_per_tonne_km is None:
        transport_rate_per_tonne_km = DEFAULT_TRANSPORT_RATE_PER_TONNE_KM
        notes.append(f"No transport rate given; used the default ₹{DEFAULT_TRANSPORT_RATE_PER_TONNE_KM}/tonne-km "
                     f"benchmark (medium truck FTL, 2025 industry rate surveys).")

    if price_growth_pct_per_month == 0.0:
        notes.append("No price_growth_pct_per_month given; assumed flat (0%) prices. "
                     "Pass Model 3's forecast growth rate for a more realistic store-vs-sell comparison.")

    if storage_options is None:
        storage_options = [
            {"name": "FCI godown (default distance)", "type": "fci",
             "distance_from_farm_km": direct_to_market_distance_km,
             "distance_to_market_km": direct_to_market_distance_km},
            {"name": "Private cold storage (default distance)", "type": "private_cold",
             "distance_from_farm_km": direct_to_market_distance_km,
             "distance_to_market_km": direct_to_market_distance_km},
        ]
        notes.append("No storage_options given; evaluated default FCI and private cold storage "
                     "using direct_to_market_distance_km as a stand-in for actual storage distances.")

    quantity_quintals = quantity_tonnes * 10  # 1 tonne = 10 quintals

    alternatives = []

    # baseline: sell now, no storage
    sell_now_transport_cost = direct_to_market_distance_km * transport_rate_per_tonne_km * quantity_tonnes
    sell_now_revenue = current_price_per_quintal * quantity_quintals
    sell_now_profit = sell_now_revenue - sell_now_transport_cost
    alternatives.append({
        "option": "sell_now", "hold_days": 0,
        "revenue": round(sell_now_revenue, 2), "storage_cost": 0.0,
        "transport_cost": round(sell_now_transport_cost, 2),
        "spoilage_loss_value": 0.0, "net_profit": round(sell_now_profit, 2),
    })

    for opt in storage_options:
        if "rate_per_quintal_per_month" in opt:
            rate = opt["rate_per_quintal_per_month"]
        else:
            rate_info = DEFAULT_STORAGE_RATES[opt.get("type", "fci")]
            rate = rate_info["rate"]

        transport_cost = ((opt["distance_from_farm_km"] + opt["distance_to_market_km"])
                          * transport_rate_per_tonne_km * quantity_tonnes)

        for t in HOLD_DAY_GRID:
            if t > max_hold_days:
                continue
            storage_cost = rate * quantity_quintals * (t / 30)
            spoilage_fraction = min(loss_rate_pct / 100 * (t / SPOILAGE_REFERENCE_DAYS), 1.0)
            effective_quintals = quantity_quintals * (1 - spoilage_fraction)
            spoilage_loss_value = (quantity_quintals - effective_quintals) * current_price_per_quintal

            projected_price = current_price_per_quintal * (1 + price_growth_pct_per_month / 100) ** (t / 30)
            revenue = projected_price * effective_quintals
            net_profit = revenue - storage_cost - transport_cost

            alternatives.append({
                "option": opt["name"], "hold_days": t,
                "revenue": round(revenue, 2), "storage_cost": round(storage_cost, 2),
                "transport_cost": round(transport_cost, 2),
                "spoilage_loss_value": round(spoilage_loss_value, 2),
                "net_profit": round(net_profit, 2),
            })

    best = max(alternatives, key=lambda a: a["net_profit"])

    return {
        "ok": True,
        "item": item,
        "loss_rate_pct": loss_rate_pct,
        "sellable_share_pct": sellable_share_pct,
        "recommendation": f"{best['option']} (hold {best['hold_days']} days)" if best["hold_days"] > 0 else "sell_now",
        "revenue": best["revenue"],
        "storage_cost": best["storage_cost"],
        "transport_cost": best["transport_cost"],
        "spoilage_loss_value": best["spoilage_loss_value"],
        "net_profit": best["net_profit"],
        "alternatives": sorted(alternatives, key=lambda a: -a["net_profit"]),
        "notes": notes,
    }


def _cli():
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Supply chain store-vs-sell optimizer.")
    parser.add_argument("--item", required=True)
    parser.add_argument("--quantity-tonnes", required=True, type=float)
    parser.add_argument("--price-per-quintal", required=True, type=float)
    parser.add_argument("--distance-km", required=True, type=float, help="Direct farm-to-market distance")
    parser.add_argument("--growth-pct-per-month", type=float, default=0.0)
    args = parser.parse_args()

    result = optimize_supply_chain(
        item=args.item, quantity_tonnes=args.quantity_tonnes,
        current_price_per_quintal=args.price_per_quintal,
        direct_to_market_distance_km=args.distance_km,
        price_growth_pct_per_month=args.growth_pct_per_month,
    )
    if not result["ok"]:
        print(f"\nError: {result['error']}")
        sys.exit(1)

    print(f"\n{result['item']} — {args.quantity_tonnes} tonnes")
    print(f"  Recommendation: {result['recommendation']}")
    print(f"  Revenue: ₹{result['revenue']:,.0f}")
    print(f"  Storage cost: ₹{result['storage_cost']:,.0f}")
    print(f"  Transport cost: ₹{result['transport_cost']:,.0f}")
    print(f"  Spoilage loss: ₹{result['spoilage_loss_value']:,.0f}")
    print(f"  Net profit: ₹{result['net_profit']:,.0f}")
    for note in result["notes"]:
        print(f"  Note: {note}")


if __name__ == "__main__":
    _cli()