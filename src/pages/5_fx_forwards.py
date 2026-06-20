"""FX Forward pricing via covered interest rate parity."""
import QuantLib as ql
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(page_title="FX Forwards – QuantLib Explorer", page_icon="💱", layout="wide")

# ── helpers ──────────────────────────────────────────────────────────────────

def fx_forward(spot, r_dom, r_for, T):
    """Covered interest rate parity: F = S * e^{(r_d - r_f)*T}"""
    today = ql.Date.todaysDate()
    ql.Settings.instance().evaluationDate = today

    spot_q   = ql.QuoteHandle(ql.SimpleQuote(spot))
    dom_ts   = ql.YieldTermStructureHandle(
        ql.FlatForward(today, ql.QuoteHandle(ql.SimpleQuote(r_dom)), ql.Actual365Fixed()))
    for_ts   = ql.YieldTermStructureHandle(
        ql.FlatForward(today, ql.QuoteHandle(ql.SimpleQuote(r_for)), ql.Actual365Fixed()))

    process = ql.GarmanKohlagenProcess(spot_q, for_ts, dom_ts,
        ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(today, ql.NullCalendar(),
                ql.QuoteHandle(ql.SimpleQuote(0.0)), ql.Actual365Fixed())))

    # Analytical: F = S * DF_for / DF_dom
    dom_df = dom_ts.discount(today + int(T * 365))
    for_df = for_ts.discount(today + int(T * 365))
    fwd = spot * for_df / dom_df
    fwd_points = fwd - spot
    annualised_cost = (fwd / spot - 1) / T * 100
    return fwd, fwd_points, annualised_cost


# ── sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.header("💱 FX Forward Parameters")
ccy_pair = st.sidebar.selectbox("Currency Pair", ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"],
    help="Base / Quote currency.")

default_spots = {"EUR/USD": 1.08, "GBP/USD": 1.27, "USD/JPY": 150.0, "AUD/USD": 0.65}
spot = st.sidebar.number_input("Spot Rate", value=default_spots[ccy_pair], format="%.4f",
    help="Current exchange rate (units of quote per 1 base).")

r_dom_pct = st.sidebar.slider("Domestic (Quote) Rate (%)", 0.0, 15.0, 5.0, 0.1,
    help="Risk-free rate of the quote currency (e.g. USD for EUR/USD).")
r_for_pct = st.sidebar.slider("Foreign (Base) Rate (%)", 0.0, 15.0, 3.5, 0.1,
    help="Risk-free rate of the base currency (e.g. EUR for EUR/USD).")
T = st.sidebar.slider("Tenor (years)", 0.02, 5.0, 1.0, 0.02,
    help="Time until settlement of the forward contract.")

r_dom = r_dom_pct / 100
r_for = r_for_pct / 100

fwd, fwd_points, ann_cost = fx_forward(spot, r_dom, r_for, T)

# ── main ─────────────────────────────────────────────────────────────────────

st.title("💱 FX Forward Pricing")
st.markdown(
    r"""
An **FX forward** fixes an exchange rate today for a currency exchange on a future date.
Under **Covered Interest Rate Parity (CIP)**, the fair forward rate is:

$$F = S \cdot \frac{e^{-r_f T}}{e^{-r_d T}} = S \cdot e^{(r_d - r_f) T}$$

where $S$ is the spot, $r_d$ the domestic rate, $r_f$ the foreign rate, and $T$ the tenor.
"""
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Spot", f"{spot:.4f}", help="Current exchange rate.")
k2.metric("Forward Rate", f"{fwd:.4f}", help="Fair forward rate derived from interest rate parity.")
k3.metric("Forward Points", f"{fwd_points*10000:+.2f} pips",
    help="Difference between forward and spot in pips (×10,000).")
k4.metric("Annualised Premium", f"{ann_cost:+.4f}%",
    help="How much the forward rate deviates from spot on an annualised basis.")

premium_label = "Premium" if fwd > spot else "Discount"
st.info(
    f"The {ccy_pair} forward is trading at a **{premium_label}** "
    f"because the domestic rate ({r_dom_pct:.2f}%) is "
    f"{'higher' if r_dom > r_for else 'lower'} than the foreign rate ({r_for_pct:.2f}%)."
)

st.divider()

# Forward rate vs tenor
tenors_range = np.linspace(0.02, 5.0, 200)
fwds  = [fx_forward(spot, r_dom, r_for, t)[0] for t in tenors_range]
pts   = [fx_forward(spot, r_dom, r_for, t)[1] * 10000 for t in tenors_range]

fig = make_subplots(rows=1, cols=2,
    subplot_titles=("Forward Rate vs Tenor", "Forward Points vs Tenor"))

fig.add_trace(go.Scatter(x=tenors_range, y=fwds, name="Forward Rate",
    line=dict(color="#1f77b4", width=2)), row=1, col=1)
fig.add_hline(y=spot, line_dash="dash", line_color="grey", annotation_text="Spot", row=1, col=1)
fig.add_vline(x=T, line_dash="dash", line_color="red", annotation_text="Selected T", row=1, col=1)

fig.add_trace(go.Scatter(x=tenors_range, y=pts, name="Fwd Points (pips)",
    fill="tozeroy", line=dict(color="#d62728"), fillcolor="rgba(214,39,40,0.1)"), row=1, col=2)
fig.add_vline(x=T, line_dash="dash", line_color="red", row=1, col=2)
fig.add_hline(y=0, line_dash="dot", line_color="grey", row=1, col=2)

fig.update_layout(height=400, template="plotly_white", showlegend=True,
    legend=dict(orientation="h", y=-0.18))
fig.update_xaxes(title_text="Tenor (yrs)", row=1, col=1)
fig.update_yaxes(title_text="Rate", row=1, col=1)
fig.update_xaxes(title_text="Tenor (yrs)", row=1, col=2)
fig.update_yaxes(title_text="Pips", row=1, col=2)
st.plotly_chart(fig, use_container_width=True)

# Rate differential surface
st.subheader("Forward Rate — Interest Rate Differential Surface")
rd_range = np.linspace(0.0, 0.12, 25)
rf_range = np.linspace(0.0, 0.12, 25)
Z = np.array([
    [fx_forward(spot, rd, rf, T)[0] for rf in rf_range]
    for rd in rd_range
])
fig2 = go.Figure(go.Surface(
    x=rf_range * 100, y=rd_range * 100, z=Z,
    colorscale="RdBu", colorbar=dict(title="Fwd Rate"),
))
fig2.update_layout(height=500, template="plotly_white",
    scene=dict(xaxis_title="Foreign Rate (%)", yaxis_title="Domestic Rate (%)",
               zaxis_title="Forward Rate"))
st.plotly_chart(fig2, use_container_width=True)

# Scenario table
st.subheader("Forward Rate Schedule")
rows = []
for t in [1/52, 1/12, 3/12, 6/12, 1, 2, 3, 5]:
    f, p, ac = fx_forward(spot, r_dom, r_for, t)
    rows.append({"Tenor": f"{t:.3f} yr", "Forward": f"{f:.5f}",
                 "Fwd Points (pips)": f"{p*10000:+.2f}",
                 "Ann. Premium (%)": f"{ac:+.4f}"})
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with st.expander("📋 QuantLib Code — FX Forward"):
    st.code("""
import QuantLib as ql

today = ql.Date.todaysDate()
ql.Settings.instance().evaluationDate = today

spot  = 1.08    # EUR/USD spot
r_dom = 0.05    # USD rate
r_for = 0.035   # EUR rate
T     = 1.0     # 1 year

dom_ts = ql.YieldTermStructureHandle(
    ql.FlatForward(today, r_dom, ql.Actual365Fixed()))
for_ts = ql.YieldTermStructureHandle(
    ql.FlatForward(today, r_for, ql.Actual365Fixed()))

settle = today + int(T * 365)
dom_df = dom_ts.discount(settle)   # e^{-r_d * T}
for_df = for_ts.discount(settle)   # e^{-r_f * T}

fwd    = spot * for_df / dom_df
print(f"Forward Rate  : {fwd:.5f}")
print(f"Forward Points: {(fwd - spot)*10000:+.2f} pips")
""", language="python")

with st.expander("📚 Key Concepts"):
    st.markdown("""
| Term | Meaning |
|---|---|
| **Covered Interest Rate Parity** | No-arbitrage condition linking spot, forward, and interest rates |
| **Forward Points** | The number of pips added to/subtracted from the spot rate |
| **Premium** | Forward > Spot (domestic rate > foreign rate) |
| **Discount** | Forward < Spot (domestic rate < foreign rate) |
| **Pip** | 1/10,000 of the exchange rate for most pairs |
""")
