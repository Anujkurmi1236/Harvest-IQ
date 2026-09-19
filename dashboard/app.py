import requests
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Harvest-IQ", page_icon="🌾", layout="wide")

CANONICAL_CROPS = [
    "Rice", "Wheat", "Maize (corn)", "Barley", "Sorghum", "Millet",
    "Cassava, fresh", "Potatoes", "Sweet potatoes", "Sugar cane",
]

# --- Sidebar: inputs ---
with st.sidebar:
    st.header("🌾 Harvest-IQ")
    api_base = st.text_input("API base URL", value="http://127.0.0.1:8000")

    st.subheader("Crop & Year")
    item = st.selectbox("Crop", CANONICAL_CROPS)
    year = st.number_input("Year", min_value=1990, max_value=2100, value=2027, step=1)
    area_harvested = st.number_input(
        "Area harvested (ha) — optional", min_value=0.0, value=0.0, step=1000.0,
        help="Leave at 0 to use this crop's historical median.",
    )

    st.subheader("This Harvest")
    quantity_tonnes = st.number_input("Quantity (tonnes)", min_value=0.1, value=10.0, step=1.0)
    current_price_per_quintal = st.number_input(
        "Current market price (₹/quintal)", min_value=0.0, value=2200.0, step=10.0,
        help="Today's real mandi/farm-gate price — the model can't know this on its own.",
    )
    direct_to_market_distance_km = st.number_input(
        "Distance to market (km)", min_value=0.0, value=12.0, step=1.0,
    )

    run_clicked = st.button("Run Analysis", type="primary", width='stretch')

st.title("Harvest-IQ: Yield → Weather → Market → Supply Chain")
st.caption(
    "Yield and weather run in parallel and are aggregated, then fed sequentially "
    "into the market forecaster and supply chain optimizer."
)

if "result" not in st.session_state:
    st.session_state.result = None

if run_clicked:
    payload = {
        "item": item,
        "year": int(year),
        "area_harvested": area_harvested if area_harvested > 0 else None,
        "quantity_tonnes": quantity_tonnes,
        "current_price_per_quintal": current_price_per_quintal,
        "direct_to_market_distance_km": direct_to_market_distance_km,
    }
    try:
        with st.spinner("Running yield + weather in parallel, then market → supply chain..."):
            resp = requests.post(f"{api_base}/forecast", json=payload, timeout=30)
        if resp.status_code != 200:
            st.error(f"API returned {resp.status_code}: {resp.text}")
            st.session_state.result = None
        else:
            st.session_state.result = resp.json()
    except requests.exceptions.ConnectionError:
        st.error(
            f"Couldn't reach the API at {api_base}. Is it running? "
            f"(`uv run fastapi dev api/main.py`)"
        )
        st.session_state.result = None

result = st.session_state.result

if result is None:
    st.info("Set your inputs in the sidebar and click **Run Analysis**.")
    st.stop()

yield_r = result.get("yield") or {}
weather_r = result.get("weather") or {}
market_r = result.get("market") or {}
supply_r = result.get("supply_chain") or {}

# --- Top-level failure banner (graceful degradation, not a crash) ---
failed_stages = [name for name, r in [("Yield", yield_r), ("Weather", weather_r),
                                        ("Market", market_r), ("Supply Chain", supply_r)]
                  if not r.get("ok", False)]
if failed_stages:
    st.warning(f"These stages did not complete successfully: {', '.join(failed_stages)}. "
               f"See their tabs for details.")

tab_yield, tab_weather, tab_market, tab_supply, tab_notes = st.tabs(
    ["🌱 Yield", "🌡️ Weather", "💰 Market", "🚚 Supply Chain", "📋 Assumptions & Notes"]
)

with tab_yield:
    if yield_r.get("ok"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Predicted Yield", f"{yield_r['predicted_yield_kg_ha']:,.0f} kg/ha")
        c2.metric("Range (low–high)", f"{yield_r['low_kg_ha']:,.0f} – {yield_r['high_kg_ha']:,.0f}")
        c3.metric("Typical Error", f"± {yield_r['typical_error_pct']:.1f}%")
        if yield_r.get("low_confidence"):
            st.caption("⚠️ Low confidence — this crop had little held-out test data.")
        st.bar_chart(pd.DataFrame({
            "kg/ha": [yield_r["low_kg_ha"], yield_r["predicted_yield_kg_ha"], yield_r["high_kg_ha"]],
        }, index=["Low", "Predicted", "High"]))
    else:
        st.error(yield_r.get("error", "Yield prediction failed."))

with tab_weather:
    if weather_r.get("ok"):
        c1, c2 = st.columns(2)
        c1.metric("Predicted Temp Change", f"{weather_r['predicted_temp_change_degC']:.3f} °C",
                   help=f"Typical error ± {weather_r.get('typical_error_degC', 0):.3f} °C")
        stress = weather_r["environmental_stress_index"]
        c2.metric("Environmental Stress Index", f"{stress:.1f} / 100")
        st.progress(min(stress / 100, 1.0))
        if weather_r.get("stress_components"):
            st.caption("Stress index components (0–100 each, higher = more stress):")
            st.dataframe(
                pd.DataFrame.from_dict(weather_r["stress_components"], orient="index", columns=["score"]),
                width='stretch',
            )
    else:
        st.error(weather_r.get("error", "Weather prediction failed."))

with tab_market:
    if market_r.get("ok"):
        if market_r.get("is_historical"):
            st.metric("Price Index Level (actual, historical)", f"{market_r['predicted_index_level']:.1f}")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Predicted Price Index", f"{market_r['predicted_index_level']:.1f}")
            c2.metric("Range (low–high)", f"{market_r['low_index_level']:.1f} – {market_r['high_index_level']:.1f}")
            c3.metric("Years Ahead", market_r.get("steps_ahead", "—"))
            st.caption(
                f"Last known ({market_r.get('last_known_year')}): "
                f"{market_r.get('last_known_index_level'):.1f}"
            )
        st.caption("Index base: 2014–2016 = 100. This is a relative price index, not a ₹ currency figure.")
    else:
        st.error(market_r.get("error", "Market forecast failed."))

with tab_supply:
    if supply_r.get("ok"):
        rec = supply_r["recommendation"]
        if rec == "sell_now":
            st.success(f"**Recommendation: Sell now**")
        else:
            st.info(f"**Recommendation: {rec}**")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Revenue", f"₹{supply_r['revenue']:,.0f}")
        c2.metric("Storage Cost", f"₹{supply_r['storage_cost']:,.0f}")
        c3.metric("Transport Cost", f"₹{supply_r['transport_cost']:,.0f}")
        c4.metric("Net Profit", f"₹{supply_r['net_profit']:,.0f}")

        st.caption(
            f"Loss rate for this crop: {supply_r.get('loss_rate_pct', 0):.1f}% · "
            f"Sellable share: {supply_r.get('sellable_share_pct', 0):.1f}%"
        )

        st.subheader("All options considered")
        alt_df = pd.DataFrame(supply_r["alternatives"])
        chosen_idx = alt_df["net_profit"].idxmax()
        st.dataframe(
            alt_df.style.apply(
                lambda row: ["background-color: #d4edda" if row.name == chosen_idx else "" for _ in row],
                axis=1,
            ),
            width='stretch',
        )
    else:
        st.error(supply_r.get("error", "Supply chain optimization failed."))

with tab_notes:
    st.caption(
        "Every assumption, fallback, or default used anywhere in the pipeline shows up here — "
        "nothing is silently substituted."
    )
    all_notes = []
    for stage, r in [("Yield", yield_r), ("Weather", weather_r), ("Market", market_r), ("Supply Chain", supply_r)]:
        for note in (r.get("notes") or []):
            all_notes.append((stage, note))
    if all_notes:
        st.table(pd.DataFrame(all_notes, columns=["Stage", "Note"]))
    else:
        st.write("No assumptions or fallbacks were needed for this run.")