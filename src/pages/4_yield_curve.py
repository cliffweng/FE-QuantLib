"""Yield curve bootstrapping from deposit and swap rates."""
import QuantLib as ql
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(page_title="Yield Curve – QuantLib Explorer", page_icon="📐", layout="wide")

# ── sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.header("📐 Market Rates")
st.sidebar.markdown("**Deposit Rates**")
d1w  = st.sidebar.slider("1W (%)",  0.1, 15.0, 4.50, 0.05)
d1m  = st.sidebar.slider("1M (%)",  0.1, 15.0, 4.60, 0.05)
d3m  = st.sidebar.slider("3M (%)",  0.1, 15.0, 4.75, 0.05)
d6m  = st.sidebar.slider("6M (%)",  0.1, 15.0, 4.85, 0.05)
st.sidebar.markdown("**Swap Rates**")
s1y  = st.sidebar.slider("1Y (%)",  0.1, 15.0, 4.90, 0.05)
s2y  = st.sidebar.slider("2Y (%)",  0.1, 15.0, 4.80, 0.05)
s3y  = st.sidebar.slider("3Y (%)",  0.1, 15.0, 4.70, 0.05)
s5y  = st.sidebar.slider("5Y (%)",  0.1, 15.0, 4.55, 0.05)
s7y  = st.sidebar.slider("7Y (%)",  0.1, 15.0, 4.45, 0.05)
s10y = st.sidebar.slider("10Y (%)", 0.1, 15.0, 4.40, 0.05)
s20y = st.sidebar.slider("20Y (%)", 0.1, 15.0, 4.50, 0.05)
s30y = st.sidebar.slider("30Y (%)", 0.1, 15.0, 4.60, 0.05)

# ── bootstrap ────────────────────────────────────────────────────────────────

def bootstrap_curve(d1w, d1m, d3m, d6m, s1y, s2y, s3y, s5y, s7y, s10y, s20y, s30y):
    today    = ql.Date.todaysDate()
    ql.Settings.instance().evaluationDate = today
    calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
    dc       = ql.Actual360()

    def dep(rate, tenor):
        return ql.DepositRateHelper(
            ql.QuoteHandle(ql.SimpleQuote(rate / 100)),
            ql.Period(tenor),
            2, calendar, ql.ModifiedFollowing, True, dc,
        )

    def swap_helper(rate, tenor):
        index = ql.USDLibor(ql.Period(3, ql.Months))
        return ql.SwapRateHelper(
            ql.QuoteHandle(ql.SimpleQuote(rate / 100)),
            ql.Period(tenor),
            calendar,
            ql.Semiannual, ql.Unadjusted,
            ql.Thirty360(ql.Thirty360.BondBasis),
            index,
        )

    helpers = [
        dep(d1w, "1W"), dep(d1m, "1M"), dep(d3m, "3M"), dep(d6m, "6M"),
        swap_helper(s1y, "1Y"), swap_helper(s2y, "2Y"),
        swap_helper(s3y, "3Y"), swap_helper(s5y, "5Y"),
        swap_helper(s7y, "7Y"), swap_helper(s10y, "10Y"),
        swap_helper(s20y, "20Y"), swap_helper(s30y, "30Y"),
    ]

    curve = ql.PiecewiseLogCubicDiscount(today, helpers, dc)
    curve.enableExtrapolation()
    return curve, today


@st.cache_data(ttl=0)
def build_curve_data(d1w, d1m, d3m, d6m, s1y, s2y, s3y, s5y, s7y, s10y, s20y, s30y):
    curve, today = bootstrap_curve(d1w, d1m, d3m, d6m, s1y, s2y, s3y, s5y, s7y, s10y, s20y, s30y)
    tenors = np.linspace(0.02, 30, 300)
    zero_rates, fwd_rates, disc_factors = [], [], []
    for t in tenors:
        d = today + int(t * 365)
        try:
            zr = curve.zeroRate(d, ql.Actual365Fixed(), ql.Continuous).rate()
            fr = curve.forwardRate(d, today + int((t + 0.25) * 365),
                                   ql.Actual365Fixed(), ql.Continuous).rate()
            df = curve.discount(d)
        except Exception:
            zr = fr = df = float("nan")
        zero_rates.append(zr * 100)
        fwd_rates.append(fr * 100)
        disc_factors.append(df)
    return tenors, zero_rates, fwd_rates, disc_factors


tenors, zero_rates, fwd_rates, disc_factors = build_curve_data(
    d1w, d1m, d3m, d6m, s1y, s2y, s3y, s5y, s7y, s10y, s20y, s30y
)

# input market points for overlay
market_tenors = [1/52, 1/12, 3/12, 6/12, 1, 2, 3, 5, 7, 10, 20, 30]
market_rates  = [d1w, d1m, d3m, d6m, s1y, s2y, s3y, s5y, s7y, s10y, s20y, s30y]

# ── main ─────────────────────────────────────────────────────────────────────

st.title("📐 Yield Curve Bootstrapping")
st.markdown(
    "**Bootstrapping** constructs a continuous yield curve from discrete market-observed "
    "deposit and swap rates. QuantLib uses **piecewise log-cubic discount factor** interpolation "
    "to produce a smooth, arbitrage-free curve."
)

fig = make_subplots(rows=2, cols=2,
    subplot_titles=("Zero Rate Curve", "Instantaneous Forward Rate",
                    "Discount Factors", "Input Rates vs Bootstrapped Zeros"))

fig.add_trace(go.Scatter(x=tenors, y=zero_rates, name="Zero Rate", line=dict(color="#1f77b4")), row=1, col=1)
fig.add_trace(go.Scatter(x=market_tenors, y=market_rates, mode="markers",
    name="Market Inputs", marker=dict(color="red", size=8)), row=1, col=1)

fig.add_trace(go.Scatter(x=tenors, y=fwd_rates, name="Fwd Rate", line=dict(color="#d62728")), row=1, col=2)

fig.add_trace(go.Scatter(x=tenors, y=disc_factors, name="Disc Factor",
    line=dict(color="#2ca02c"), fill="tozeroy", fillcolor="rgba(44,160,44,0.1)"), row=2, col=1)

fig.add_trace(go.Scatter(x=market_tenors, y=market_rates, name="Par Rates",
    mode="lines+markers", line=dict(color="#ff7f0e", dash="dot"),
    marker=dict(size=7)), row=2, col=2)

# bootstrapped zeros at market tenors
zs_at_market = []
curve, today_c = bootstrap_curve(d1w, d1m, d3m, d6m, s1y, s2y, s3y, s5y, s7y, s10y, s20y, s30y)
for t in market_tenors:
    d = today_c + int(t * 365)
    try:
        zr = curve.zeroRate(d, ql.Actual365Fixed(), ql.Continuous).rate() * 100
    except Exception:
        zr = float("nan")
    zs_at_market.append(zr)

fig.add_trace(go.Scatter(x=market_tenors, y=zs_at_market, name="Zero Rates",
    mode="lines+markers", line=dict(color="#1f77b4"),
    marker=dict(size=7)), row=2, col=2)

fig.update_layout(height=600, template="plotly_white", legend=dict(orientation="h", y=-0.1))
for r, c, xl, yl in [(1,1,"Tenor (yrs)","Rate (%)"), (1,2,"Tenor (yrs)","Fwd Rate (%)"),
                      (2,1,"Tenor (yrs)","Discount Factor"), (2,2,"Tenor (yrs)","Rate (%)")]:
    fig.update_xaxes(title_text=xl, row=r, col=c)
    fig.update_yaxes(title_text=yl, row=r, col=c)
st.plotly_chart(fig, use_container_width=True)

# Table
st.subheader("Curve Snapshot")
snap_tenors = [0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30]
rows = []
for t in snap_tenors:
    d = today_c + int(t * 365)
    try:
        zr = curve.zeroRate(d, ql.Actual365Fixed(), ql.Continuous).rate() * 100
        fr = curve.forwardRate(d, today_c + int((t + 0.25) * 365),
                               ql.Actual365Fixed(), ql.Continuous).rate() * 100
        df = curve.discount(d)
    except Exception:
        zr = fr = df = float("nan")
    rows.append({"Tenor (yrs)": t, "Zero Rate (%)": f"{zr:.4f}",
                 "Fwd Rate (%)": f"{fr:.4f}", "Discount Factor": f"{df:.6f}"})
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with st.expander("📋 QuantLib Code — Yield Curve Bootstrap"):
    st.code("""
import QuantLib as ql

today    = ql.Date.todaysDate()
ql.Settings.instance().evaluationDate = today
calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
dc       = ql.Actual360()

def dep(rate, tenor):
    return ql.DepositRateHelper(
        ql.QuoteHandle(ql.SimpleQuote(rate)),
        ql.Period(tenor), 2, calendar,
        ql.ModifiedFollowing, True, dc)

def sw(rate, tenor):
    idx = ql.USDLibor(ql.Period(3, ql.Months))
    return ql.SwapRateHelper(
        ql.QuoteHandle(ql.SimpleQuote(rate)),
        ql.Period(tenor), calendar,
        ql.Semiannual, ql.Unadjusted,
        ql.Thirty360(ql.Thirty360.BondBasis), idx)

helpers = [
    dep(0.045, "3M"), dep(0.048, "6M"),
    sw(0.049, "1Y"),  sw(0.048, "2Y"),
    sw(0.047, "5Y"),  sw(0.044, "10Y"),
    sw(0.046, "30Y"),
]

curve = ql.PiecewiseLogCubicDiscount(today, helpers, dc)
curve.enableExtrapolation()

d10y = today + int(10 * 365)
print(f"10Y Zero : {curve.zeroRate(d10y, ql.Actual365Fixed(), ql.Continuous).rate()*100:.4f}%")
print(f"10Y DF   : {curve.discount(d10y):.6f}")
""", language="python")

with st.expander("📚 Key Concepts"):
    st.markdown("""
| Term | Meaning |
|---|---|
| **Zero rate** | Spot rate from today to a single future date (continuously compounded) |
| **Forward rate** | Implied rate between two future dates |
| **Discount factor** | PV of $1 received at a future date: DF = e^{-r·t} |
| **Par / swap rate** | The coupon rate that makes a bond / swap worth par today |
| **Bootstrapping** | Iteratively solving for zero rates from short to long tenors using market instruments |
""")
