"""Bond pricing: price-yield curve, YTM, duration, convexity."""
import QuantLib as ql
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(page_title="Bonds – QuantLib Explorer", page_icon="🏦", layout="wide")

# ── helpers ──────────────────────────────────────────────────────────────────

def make_bond(face, coupon_rate, maturity_years, freq, settlement_days=2):
    today = ql.Date.todaysDate()
    ql.Settings.instance().evaluationDate = today
    calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
    maturity = calendar.advance(today, ql.Period(maturity_years, ql.Years))
    schedule = ql.Schedule(
        today, maturity,
        ql.Period(freq),
        calendar,
        ql.Unadjusted, ql.Unadjusted,
        ql.DateGeneration.Backward, False,
    )
    bond = ql.FixedRateBond(settlement_days, face, schedule, [coupon_rate], ql.ActualActual(ql.ActualActual.ISDA))
    return bond, today


def price_bond(bond, ytm, freq):
    return ql.BondFunctions.cleanPrice(bond, ql.InterestRate(ytm, ql.ActualActual(ql.ActualActual.ISDA), ql.Compounded, freq))


def bond_metrics(bond, ytm, freq, face):
    ir = ql.InterestRate(ytm, ql.ActualActual(ql.ActualActual.ISDA), ql.Compounded, freq)
    # QuantLib cleanPrice is per 100 of face; scale to actual dollar amount
    price_per100 = ql.BondFunctions.cleanPrice(bond, ir)
    price = price_per100 * face / 100
    duration = ql.BondFunctions.duration(bond, ir, ql.Duration.Modified)
    convexity = ql.BondFunctions.convexity(bond, ir)
    return price, duration, convexity


def price_yield_curve(bond, freq, face, ytm_min=0.001, ytm_max=0.20, n=200):
    ytms = np.linspace(ytm_min, ytm_max, n)
    prices = [price_bond(bond, y, freq) * face / 100 for y in ytms]
    return ytms, prices


# ── sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.header("🏦 Bond Parameters")
face = st.sidebar.number_input("Face Value ($)", min_value=100, max_value=10_000, value=1000, step=100,
    help="The par / principal amount repaid at maturity.")
coupon_pct = st.sidebar.slider("Coupon Rate (%)", 0.5, 15.0, 5.0, 0.25,
    help="Annual coupon rate expressed as a percentage of face value.")
maturity_years = st.sidebar.slider("Maturity (years)", 1, 30, 10,
    help="Number of years until the bond matures.")
freq_label = st.sidebar.selectbox("Coupon Frequency", ["Annual", "Semi-Annual", "Quarterly"],
    help="How often coupon payments are made per year.")
ytm_pct = st.sidebar.slider("Yield to Maturity (%)", 0.1, 20.0, 5.0, 0.1,
    help="The discount rate used to price the bond. When YTM = coupon rate, price ≈ par.")

freq_map = {"Annual": ql.Annual, "Semi-Annual": ql.Semiannual, "Quarterly": ql.Quarterly}
freq = freq_map[freq_label]
coupon_rate = coupon_pct / 100
ytm = ytm_pct / 100

bond, today = make_bond(face, coupon_rate, maturity_years, freq)
price, duration, convexity = bond_metrics(bond, ytm, freq, face)
ytms, prices = price_yield_curve(bond, freq, face)

# ── main ─────────────────────────────────────────────────────────────────────

st.title("🏦 Fixed-Rate Bond Pricing")
st.markdown(
    "A **fixed-rate bond** pays a constant coupon periodically and returns the face value at maturity. "
    "The fair price is the present value of all future cash flows discounted at the **Yield to Maturity (YTM)**."
)

# KPI row
k1, k2, k3, k4 = st.columns(4)
k1.metric("Clean Price", f"${price:,.2f}", help="Present value of coupons + principal, excluding accrued interest.")
k2.metric("Price / Par", f"{price/face*100:.2f}%", help="Whether the bond trades at a premium (>100%), par (=100%), or discount (<100%).")
k3.metric("Modified Duration", f"{duration:.3f} yrs", help="% price change for a 1% parallel shift in yield.")
k4.metric("Convexity", f"{convexity:.3f}", help="Second-order price sensitivity — higher convexity is better for the holder.")

st.divider()

# Price-yield curve
fig = make_subplots(rows=1, cols=2, subplot_titles=("Price–Yield Curve", "Cash Flow Schedule"))

fig.add_trace(go.Scatter(
    x=[y * 100 for y in ytms], y=prices,
    mode="lines", name="Bond Price",
    line=dict(color="#1f77b4", width=2),
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=[ytm_pct], y=[price],
    mode="markers", name="Current",
    marker=dict(color="red", size=10, symbol="star"),
), row=1, col=1)

fig.add_hline(y=face, line_dash="dash", line_color="grey", annotation_text="Par", row=1, col=1)

# Cash flows
cf_dates = bond.cashflows()
cf_df = pd.DataFrame(
    [(cf.date().ISO(), cf.amount()) for cf in cf_dates if cf.amount() > 0],
    columns=["Date", "Amount"],
)
colors = ["#d62728" if v == cf_df["Amount"].max() else "#1f77b4" for v in cf_df["Amount"]]
fig.add_trace(go.Bar(x=cf_df["Date"], y=cf_df["Amount"], name="Cash Flow",
    marker_color=colors), row=1, col=2)

fig.update_layout(height=420, showlegend=True, template="plotly_white",
    legend=dict(orientation="h", y=-0.15))
fig.update_xaxes(title_text="YTM (%)", row=1, col=1)
fig.update_yaxes(title_text="Clean Price ($)", row=1, col=1)
fig.update_xaxes(title_text="Date", row=1, col=2)
fig.update_yaxes(title_text="Amount ($)", row=1, col=2)
st.plotly_chart(fig, use_container_width=True)

# Duration / convexity illustration
st.subheader("Duration & Convexity Sensitivity")
st.markdown(
    r"""
The **modified duration** approximates the *linear* price change:

$$\Delta P \approx -D_{\text{mod}} \cdot P \cdot \Delta y$$

**Convexity** adds the second-order correction:

$$\Delta P \approx -D_{\text{mod}} \cdot P \cdot \Delta y + \tfrac{1}{2} \cdot C \cdot P \cdot (\Delta y)^2$$

The chart below shows both approximations vs the exact price.
"""
)

dy_range = np.linspace(-0.05, 0.05, 200)
exact = [price_bond(bond, max(0.0001, ytm + dy), freq) * face / 100 for dy in dy_range]
linear = [price - duration * price * dy for dy in dy_range]
convex = [price - duration * price * dy + 0.5 * convexity * price * dy**2 for dy in dy_range]

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=dy_range * 100, y=exact, name="Exact Price", line=dict(color="#1f77b4", width=2)))
fig2.add_trace(go.Scatter(x=dy_range * 100, y=linear, name="Duration Only", line=dict(color="#ff7f0e", dash="dash")))
fig2.add_trace(go.Scatter(x=dy_range * 100, y=convex, name="Duration + Convexity", line=dict(color="#2ca02c", dash="dot")))
fig2.add_vline(x=0, line_dash="dash", line_color="grey")
fig2.update_layout(height=380, template="plotly_white",
    xaxis_title="Yield Change (Δy, %)", yaxis_title="Price ($)",
    legend=dict(orientation="h", y=-0.2))
st.plotly_chart(fig2, use_container_width=True)

# Sensitivity table
st.subheader("Sensitivity Table")
shifts = [-200, -100, -50, -25, 0, 25, 50, 100, 200]
rows = []
for bp in shifts:
    dy = bp / 10000
    p = price_bond(bond, max(0.0001, ytm + dy), freq) * face / 100
    rows.append({"Yield Shift (bps)": bp, "YTM (%)": f"{(ytm+dy)*100:.2f}", "Price ($)": f"{p:,.4f}",
                 "P&L ($)": f"{p - price:+,.4f}", "P&L (%)": f"{(p/price - 1)*100:+.4f}"})
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# Code snippet
with st.expander("📋 QuantLib Code — Bond Pricing", expanded=False):
    st.code("""
import QuantLib as ql

today = ql.Date.todaysDate()
ql.Settings.instance().evaluationDate = today

face        = 1000
coupon_rate = 0.05          # 5 % annual coupon
maturity    = ql.Date(20, 6, 2036)
calendar    = ql.UnitedStates(ql.UnitedStates.GovernmentBond)

schedule = ql.Schedule(
    today, maturity,
    ql.Period(ql.Semiannual),
    calendar,
    ql.Unadjusted, ql.Unadjusted,
    ql.DateGeneration.Backward, False,
)

bond = ql.FixedRateBond(
    2,           # settlement days
    face,
    schedule,
    [coupon_rate],
    ql.ActualActual(ql.ActualActual.ISDA),
)

ytm = 0.05      # 5 % YTM
ir  = ql.InterestRate(ytm, ql.ActualActual(ql.ActualActual.ISDA),
                      ql.Compounded, ql.Semiannual)

price     = ql.BondFunctions.cleanPrice(bond, ir)
duration  = ql.BondFunctions.duration(bond, ir, ql.Duration.Modified)
convexity = ql.BondFunctions.convexity(bond, ir)

print(f"Clean Price : {price:.4f}")
print(f"Duration    : {duration:.4f}")
print(f"Convexity   : {convexity:.4f}")
""", language="python")

with st.expander("📚 Key Concepts", expanded=False):
    st.markdown(
        """
| Term | Definition |
|---|---|
| **Clean Price** | Bond price excluding accrued interest |
| **Dirty Price** | Clean price + accrued interest (what you actually pay) |
| **YTM** | The single discount rate that equates the PV of cash flows to the market price |
| **Modified Duration** | Approximate % price change per 1% change in yield |
| **Convexity** | Measures the curvature of the price-yield relationship; always positive for plain bonds |
| **Premium / Discount** | Coupon > YTM → price > par (premium); Coupon < YTM → price < par (discount) |
"""
    )
