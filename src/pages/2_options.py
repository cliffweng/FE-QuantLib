"""Options: Black-Scholes pricing, Greeks, payoff diagrams, volatility surface."""
import QuantLib as ql
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(page_title="Options – QuantLib Explorer", page_icon="📊", layout="wide")

# ── helpers ──────────────────────────────────────────────────────────────────

def bs_price_greeks(S, K, r, q, sigma, T, option_type, exercise="European"):
    today = ql.Date.todaysDate()
    ql.Settings.instance().evaluationDate = today
    expiry = today + int(T * 365)

    payoff = ql.PlainVanillaPayoff(
        ql.Option.Call if option_type == "Call" else ql.Option.Put, K
    )
    exercise_obj = (
        ql.EuropeanExercise(expiry) if exercise == "European"
        else ql.AmericanExercise(today, expiry)
    )
    option = ql.VanillaOption(payoff, exercise_obj)

    spot_handle = ql.QuoteHandle(ql.SimpleQuote(S))
    flat_ts = ql.YieldTermStructureHandle(
        ql.FlatForward(today, ql.QuoteHandle(ql.SimpleQuote(r)), ql.Actual365Fixed())
    )
    div_ts = ql.YieldTermStructureHandle(
        ql.FlatForward(today, ql.QuoteHandle(ql.SimpleQuote(q)), ql.Actual365Fixed())
    )
    vol_ts = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(today, ql.NullCalendar(), ql.QuoteHandle(ql.SimpleQuote(sigma)), ql.Actual365Fixed())
    )
    process = ql.BlackScholesMertonProcess(spot_handle, div_ts, flat_ts, vol_ts)

    if exercise == "European":
        option.setPricingEngine(ql.AnalyticEuropeanEngine(process))
    else:
        option.setPricingEngine(ql.FdBlackScholesVanillaEngine(process, 200, 200))

    price = option.NPV()
    try:
        delta = option.delta()
        gamma = option.gamma()
        theta = option.theta() / 365
        vega  = option.vega() / 100
        rho   = option.rho() / 100
    except Exception:
        delta = gamma = theta = vega = rho = float("nan")

    return price, delta, gamma, theta, vega, rho


# ── sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.header("📊 Option Parameters")
option_type = st.sidebar.radio("Option Type", ["Call", "Put"], horizontal=True,
    help="Call = right to BUY the underlying. Put = right to SELL.")
exercise = st.sidebar.radio("Exercise Style", ["European", "American"], horizontal=True,
    help="European can only be exercised at expiry. American can be exercised anytime.")
S = st.sidebar.slider("Spot Price (S)", 50.0, 200.0, 100.0, 1.0, help="Current market price of the underlying.")
K = st.sidebar.slider("Strike Price (K)", 50.0, 200.0, 100.0, 1.0, help="Price at which the option can be exercised.")
T = st.sidebar.slider("Time to Expiry (years)", 0.05, 3.0, 1.0, 0.05, help="Years until the option expires.")
sigma = st.sidebar.slider("Volatility σ (%)", 1.0, 100.0, 20.0, 1.0,
    help="Annualised implied volatility of the underlying.") / 100
r = st.sidebar.slider("Risk-Free Rate (%)", 0.0, 15.0, 5.0, 0.25,
    help="Continuously compounded risk-free interest rate.") / 100
q = st.sidebar.slider("Dividend Yield (%)", 0.0, 10.0, 0.0, 0.25,
    help="Continuous dividend yield of the underlying.") / 100

price, delta, gamma, theta, vega, rho = bs_price_greeks(S, K, r, q, sigma, T, option_type, exercise)

# ── main ─────────────────────────────────────────────────────────────────────

st.title("📊 Options Pricing — Black-Scholes / FD")
st.markdown(
    "Price European options analytically with **Black-Scholes-Merton** and American options with a "
    "**finite-difference** (Crank-Nicolson) scheme. Explore Greeks and payoff diagrams interactively."
)

# KPIs
cols = st.columns(6)
labels = ["Price", "Delta δ", "Gamma Γ", "Theta Θ/day", "Vega ν / 1%", "Rho ρ / 1%"]
vals   = [price, delta, gamma, theta, vega, rho]
fmts   = ["${:.4f}", "{:.4f}", "{:.5f}", "${:.4f}", "${:.4f}", "${:.4f}"]
helps  = [
    "Option's fair value today.",
    "Price change per $1 move in spot.",
    "Rate of change of delta per $1 move.",
    "Price decay per calendar day.",
    "Price change per 1% rise in vol.",
    "Price change per 1% rise in rate.",
]
for col, lbl, v, fmt, h in zip(cols, labels, vals, fmts, helps):
    col.metric(lbl, fmt.format(v), help=h)

st.divider()

# Payoff + price vs spot
spots = np.linspace(max(1, S * 0.4), S * 1.6, 300)
payoffs_at_expiry = [max(0, (s - K) if option_type == "Call" else (K - s)) for s in spots]
prices_now = [bs_price_greeks(s, K, r, q, sigma, T, option_type, exercise)[0] for s in spots]
intrinsic   = [max(0, (s - K) if option_type == "Call" else (K - s)) for s in spots]

fig = make_subplots(rows=1, cols=2,
    subplot_titles=("Payoff & Value vs Spot", "Greeks vs Spot"))

fig.add_trace(go.Scatter(x=spots, y=payoffs_at_expiry, name="Payoff at Expiry",
    line=dict(color="grey", dash="dot")), row=1, col=1)
fig.add_trace(go.Scatter(x=spots, y=prices_now, name="Option Value (now)",
    line=dict(color="#1f77b4", width=2)), row=1, col=1)
fig.add_trace(go.Scatter(x=spots, y=intrinsic, name="Intrinsic Value",
    line=dict(color="#ff7f0e", dash="dash")), row=1, col=1)
fig.add_vline(x=S, line_dash="dash", line_color="red", annotation_text="Spot", row=1, col=1)
fig.add_vline(x=K, line_dash="dash", line_color="green", annotation_text="Strike", row=1, col=1)

deltas = [bs_price_greeks(s, K, r, q, sigma, T, option_type, exercise)[1] for s in spots]
gammas = [bs_price_greeks(s, K, r, q, sigma, T, option_type, exercise)[2] * 10 for s in spots]
fig.add_trace(go.Scatter(x=spots, y=deltas, name="Delta", line=dict(color="#2ca02c")), row=1, col=2)
fig.add_trace(go.Scatter(x=spots, y=gammas, name="Gamma × 10", line=dict(color="#d62728")), row=1, col=2)
fig.add_vline(x=S, line_dash="dash", line_color="red", row=1, col=2)
fig.add_vline(x=K, line_dash="dash", line_color="green", row=1, col=2)

fig.update_layout(height=420, template="plotly_white", legend=dict(orientation="h", y=-0.18))
fig.update_xaxes(title_text="Spot ($)", row=1, col=1)
fig.update_yaxes(title_text="Value ($)", row=1, col=1)
fig.update_xaxes(title_text="Spot ($)", row=1, col=2)
st.plotly_chart(fig, use_container_width=True)

# Volatility surface
st.subheader("Volatility Surface — Option Price vs σ and T")
vols_range = np.linspace(0.05, 0.80, 30)
T_range    = np.linspace(0.08, 3.0, 30)
Z = np.array([
    [bs_price_greeks(S, K, r, q, v, t, option_type, exercise)[0] for v in vols_range]
    for t in T_range
])
fig3 = go.Figure(go.Surface(
    x=vols_range * 100, y=T_range, z=Z,
    colorscale="Viridis", colorbar=dict(title="Price ($)"),
))
fig3.update_layout(height=500, template="plotly_white",
    scene=dict(xaxis_title="Vol (%)", yaxis_title="Time (yrs)", zaxis_title="Price ($)"))
st.plotly_chart(fig3, use_container_width=True)

# P&L table (long option at current price)
st.subheader("P&L at Expiry — Scenarios")
scenario_spots = [S * m for m in [0.7, 0.8, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2, 1.3]]
rows = []
for ss in scenario_spots:
    payout = max(0, (ss - K) if option_type == "Call" else (K - ss))
    pnl = payout - price
    rows.append({"Spot at Expiry ($)": f"{ss:.2f}", "Payout ($)": f"{payout:.4f}",
                 "Net P&L ($)": f"{pnl:+.4f}", "Return": f"{pnl/price*100:+.1f}%"})
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with st.expander("📋 QuantLib Code — Black-Scholes European Option"):
    st.code("""
import QuantLib as ql

today = ql.Date.todaysDate()
ql.Settings.instance().evaluationDate = today

S, K, r, q, sigma, T = 100, 100, 0.05, 0.0, 0.20, 1.0
expiry = today + int(T * 365)

payoff   = ql.PlainVanillaPayoff(ql.Option.Call, K)
exercise = ql.EuropeanExercise(expiry)
option   = ql.VanillaOption(payoff, exercise)

process = ql.BlackScholesMertonProcess(
    ql.QuoteHandle(ql.SimpleQuote(S)),
    ql.YieldTermStructureHandle(ql.FlatForward(today, q, ql.Actual365Fixed())),
    ql.YieldTermStructureHandle(ql.FlatForward(today, r, ql.Actual365Fixed())),
    ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(today, ql.NullCalendar(), sigma, ql.Actual365Fixed())
    ),
)

option.setPricingEngine(ql.AnalyticEuropeanEngine(process))
print(f"Price : {option.NPV():.4f}")
print(f"Delta : {option.delta():.4f}")
print(f"Gamma : {option.gamma():.5f}")
print(f"Vega  : {option.vega()/100:.4f}  (per 1% vol change)")
print(f"Theta : {option.theta()/365:.4f}  (per day)")
""", language="python")

with st.expander("📚 Key Concepts"):
    st.markdown("""
| Greek | Symbol | Meaning |
|---|---|---|
| **Delta** | δ | ∂Price/∂Spot — hedge ratio |
| **Gamma** | Γ | ∂²Price/∂Spot² — rate of delta change |
| **Theta** | Θ | ∂Price/∂t — time decay (negative for long) |
| **Vega** | ν | ∂Price/∂σ — vol sensitivity |
| **Rho** | ρ | ∂Price/∂r — rate sensitivity |

**Moneyness**: ITM = In-The-Money, ATM = At-The-Money, OTM = Out-of-The-Money.
For a call: ITM when Spot > Strike.
""")
