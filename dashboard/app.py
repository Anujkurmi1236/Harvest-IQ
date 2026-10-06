import requests
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

st.set_page_config(page_title="Harvest IQ", page_icon=":material/eco:", layout="wide")

st.markdown(
    """
    <style>
        .stApp {
            background:
                radial-gradient(circle at 88% 5%, rgba(154, 213, 177, 0.26), transparent 28rem),
                linear-gradient(180deg, #f7fbf7 0%, #eef6f1 100%);
        }
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #113b2d 0%, #1d5641 100%);
        }
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stSelectbox,
        [data-testid="stSidebar"] .stNumberInput {
            color: #f3f8f5 !important;
        }
        [data-testid="stSidebar"] [data-testid="stForm"] {
            border: 1px solid rgba(220, 248, 226, 0.18);
            border-radius: 0.8rem;
            padding: 0.85rem 0.85rem 0.25rem;
            background: rgba(8, 43, 31, 0.22);
        }
        [data-testid="stSidebar"] .stButton button {
            border: 0;
            box-shadow: 0 8px 18px rgba(7, 30, 21, 0.22);
        }
        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid #d9e8dd;
            border-radius: 0.8rem;
            padding: 0.85rem 1rem;
            box-shadow: 0 8px 22px rgba(24, 72, 56, 0.05);
        }
        [data-testid="stMetricLabel"] {
            color: #557061;
            font-size: 0.78rem;
        }
        [data-testid="stMetricValue"] {
            color: #143327;
        }
        .section-kicker {
            color: #3e775d;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.13em;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
        }
        .empty-state {
            border: 1px dashed #b9d3c1;
            border-radius: 1rem;
            padding: 2.5rem 1.5rem;
            text-align: center;
            background: rgba(255, 255, 255, 0.56);
        }
        .empty-state h3 {
            color: #1c513b;
            margin: 0.5rem 0 0.35rem;
        }
        .empty-state p {
            color: #557061;
            margin: 0;
        }
        .hero-panel {
            background: linear-gradient(135deg, rgba(28, 94, 71, 0.96), rgba(56, 147, 102, 0.86));
            border-radius: 1rem;
            padding: 1.5rem 1.5rem 1rem 1.5rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 12px 32px rgba(26, 73, 58, 0.14);
        }
        .eyebrow {
            font-size: 0.72rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: rgba(255,255,255,0.78);
            margin-bottom: 0.5rem;
            font-weight: 700;
        }
        .hero-panel h2 {
            margin: 0;
            color: white;
            font-size: clamp(1.8rem, 2vw, 2.5rem);
            line-height: 1.15;
        }
        .hero-panel p {
            color: rgba(255,255,255,0.88);
            margin-top: 0.7rem;
            margin-bottom: 0;
            font-size: 1rem;
        }
        .info-chip {
            display: inline-block;
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 999px;
            padding: 0.4rem 0.8rem;
            color: #edf9f0;
            font-size: 0.78rem;
            margin-right: 0.45rem;
            margin-top: 0.75rem;
        }
        .stTabs [role="tablist"] {
            gap: 0.5rem;
        }
        .stTabs [role="tab"] {
            background: rgba(255,255,255,0.5);
            border-radius: 0.8rem 0.8rem 0 0;
            padding: 0.55rem 0.9rem;
        }
        .stTabs [role="tab"][aria-selected="true"] {
            background: #ffffff;
            border: 1px solid rgba(25, 63, 51, 0.09);
            box-shadow: 0 8px 20px rgba(24, 72, 56, 0.08);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

CANONICAL_CROPS = [
    "Rice", "Wheat", "Maize (corn)", "Barley", "Sorghum", "Millet",
    "Cassava, fresh", "Potatoes", "Sweet potatoes", "Sugar cane",
]

# --- Sidebar: inputs ---
with st.sidebar:
    st.markdown(
        """
        <div style="padding: 0.3rem 0 1rem 0;">
            <div style="display: flex; align-items: center; gap: 0.7rem; margin-bottom: 0.25rem;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: #9be1af; box-shadow: 0 0 18px rgba(155,225,175,0.8);"></div>
                <div style="font-weight: 800; font-size: 1.4rem; color: #f3f8f5;">Harvest IQ</div>
            </div>
            <div style="font-size: 0.8rem; color: rgba(243,248,245,0.75); letter-spacing: 0.08em; text-transform: uppercase;">Farm planning cockpit</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    api_base = st.text_input("API base URL", value=st.secrets.get("RENDER_URL"), help="Where the backend API is running.")

    with st.form("forecast_inputs"):
        st.markdown("**Forecast inputs**")
        item = st.selectbox("Crop", CANONICAL_CROPS)
        year = st.number_input("Target year", min_value=1990, max_value=2100, value=2027, step=1)
        area_harvested = st.number_input(
            "Area harvested (ha) - optional", min_value=0.0, value=0.0, step=1000.0,
            help="Leave at 0 to use this crop's historical median.",
        )
        st.caption("Harvest economics")
        quantity_tonnes = st.number_input("Quantity (tonnes)", min_value=0.1, value=10.0, step=1.0)
        current_price_per_quintal = st.number_input(
            "Current market price (INR/quintal)", min_value=0.0, value=2200.0, step=10.0,
            help="Today's real mandi/farm-gate price - the model can't know this on its own.",
        )
        direct_to_market_distance_km = st.number_input(
            "Distance to market (km)", min_value=0.0, value=12.0, step=1.0,
        )
        run_clicked = st.form_submit_button("Run analysis", type="primary", width="stretch")

st.markdown(
    """
    <div class="hero-panel">
        <div class="eyebrow">Field intelligence / decision support</div>
        <h2>See the whole harvest before you make the next move.</h2>
        <p>One grounded outlook across production, climate stress, market timing, and delivery economics.</p>
        <div>
            <span class="info-chip">Yield</span>
            <span class="info-chip">Weather</span>
            <span class="info-chip">Market</span>
            <span class="info-chip">Supply chain</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
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
            resp = requests.post(f"{api_base}/forecast", json=payload, timeout=120)
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
    except requests.exceptions.Timeout:
        st.error(
            "The API took too long to respond. Render may be waking up; "
            "please wait a moment and run the analysis again."
        )
        st.session_state.result = None

result = st.session_state.result

if result is None:
    st.markdown(
        """
        <div class="empty-state">
            <div style="font-size: 2rem; color: #2b8159;">✦</div>
            <h3>Your harvest outlook is ready to generate</h3>
            <p>Choose a crop and enter the harvest economics in the sidebar to see the forecast.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
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

st.markdown('<div class="section-kicker">Run snapshot</div>', unsafe_allow_html=True)
summary_cols = st.columns(4)
summary_cols[0].metric("Crop", item, border=True)
summary_cols[1].metric("Target year", str(year), border=True)
summary_cols[2].metric("Quantity", f"{quantity_tonnes:,.0f} t", border=True)
summary_cols[3].metric("Market distance", f"{direct_to_market_distance_km:,.0f} km", border=True)

tab_yield, tab_weather, tab_market, tab_supply, tab_notes = st.tabs(
    [":material/grass: Yield", ":material/thermostat: Weather", ":material/monitoring: Market", ":material/local_shipping: Supply chain", ":material/description: Assumptions & notes"]
)

with tab_yield:
    if yield_r.get("ok"):
        with st.container(border=True):
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
        with st.container(border=True):
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
        with st.container(border=True):
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
        with st.container(border=True):
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