"""Vanilla interest rate swap: NPV, DV01, rate sensitivity."""
import QuantLib as ql
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(page_title="IRS – QuantLib Explorer", page_icon="🔄", layout="wide")

# ── helpers ──────────────────────────────────────────────────────────────────

def _make_index(flat_curve):
    """Synthetic 3M floating index with 0-day fixing lag — no historical fixings needed."""
    calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
    today = ql.Date.todaysDate()
    return ql.IborIndex(
        "SOFR3M", ql.Period(3, ql.Months), 0,
        ql.USDCurrency(), calendar,
        ql.ModifiedFollowing, False, ql.Actual360(), flat_curve,
    )


def build_swap(notional, fixed_rate, tenor_years, pay_fixed=True):
    today = ql.Date.todaysDate()
    ql.Settings.instance().evaluationDate = today
    calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
    settlement = calendar.advance(today, ql.Period(2, ql.Days))
    maturity   = calendar.advance(settlement, ql.Period(tenor_years, ql.Years))

    fixed_schedule = ql.Schedule(
        settlement, maturity, ql.Period(ql.Semiannual), calendar,
        ql.ModifiedFollowing, ql.ModifiedFollowing,
        ql.DateGeneration.Forward, False,
    )
    float_schedule = ql.Schedule(
        settlement, maturity, ql.Period(ql.Quarterly), calendar,
        ql.ModifiedFollowing, ql.ModifiedFollowing,
        ql.DateGeneration.Forward, False,
    )

    # Placeholder index — rebuilt with live curve inside price_swap
    placeholder = ql.IborIndex(
        "SOFR3M", ql.Period(3, ql.Months), 0,
        ql.USDCurrency(), calendar,
        ql.ModifiedFollowing, False, ql.Actual360(),
    )
    swap_type = ql.VanillaSwap.Payer if pay_fixed else ql.VanillaSwap.Receiver
    swap = ql.VanillaSwap(
        swap_type, notional,
        fixed_schedule, fixed_rate, ql.Thirty360(ql.Thirty360.BondBasis),
        float_schedule, placeholder, 0.0, ql.Actual360(),
    )
    return swap, today, settlement, maturity


def price_swap(swap, libor_rate):
    today = ql.Date.todaysDate()
    flat_curve = ql.YieldTermStructureHandle(
        ql.FlatForward(today, libor_rate, ql.Actual360())
    )
    index = _make_index(flat_curve)

    notional   = swap.nominal()
    fixed_rate = swap.fixedRate()
    fixed_sch  = swap.fixedSchedule()
    float_sch  = swap.floatingSchedule()
    swap2 = ql.VanillaSwap(
        swap.type(), notional,
        fixed_sch, fixed_rate, ql.Thirty360(ql.Thirty360.BondBasis),
        float_sch, index, 0.0, ql.Actual360(),
    )
    swap2.setPricingEngine(ql.DiscountingSwapEngine(flat_curve))
    return swap2.NPV(), swap2.fairRate(), swap2


def swap_npv_vs_rate(notional, fixed_rate, tenor_years, pay_fixed, rates):
    npvs = []
    for r in rates:
        swap, _, _, _ = build_swap(notional, fixed_rate, tenor_years, pay_fixed)
        npv, _, _ = price_swap(swap, r)
        npvs.append(npv)
    return npvs


# ── sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.header("🔄 Swap Parameters")
notional = st.sidebar.number_input("Notional ($)", min_value=100_000, max_value=100_000_000,
    value=10_000_000, step=1_000_000, help="The reference principal (not exchanged).")
fixed_pct = st.sidebar.slider("Fixed Rate (%)", 0.5, 15.0, 4.0, 0.25,
    help="The fixed leg coupon rate.")
tenor = st.sidebar.slider("Tenor (years)", 1, 30, 5,
    help="Length of the swap.")
libor_pct = st.sidebar.slider("Current LIBOR / SOFR (%)", 0.1, 15.0, 4.5, 0.1,
    help="Flat rate used to discount cash flows and project floating coupons.")
pay_fixed = st.sidebar.radio("Position", ["Pay Fixed (receive float)", "Receive Fixed (pay float)"],
    help="Pay-fixed = long duration risk. Receive-fixed = short duration risk.") == "Pay Fixed (receive float)"

fixed_rate = fixed_pct / 100
libor_rate = libor_pct / 100

swap, today, settlement, maturity = build_swap(notional, fixed_rate, tenor, pay_fixed)
npv, fair_rate, priced_swap = price_swap(swap, libor_rate)

# DV01 (bump-and-reprice by 1 bp)
swap_up, _, _, _ = build_swap(notional, fixed_rate, tenor, pay_fixed)
npv_up, _, _ = price_swap(swap_up, libor_rate + 0.0001)
dv01 = npv_up - npv

# ── main ─────────────────────────────────────────────────────────────────────

st.title("🔄 Vanilla Interest Rate Swap")
st.markdown(
    "A **vanilla IRS** exchanges a **fixed** stream of cash flows for a **floating** stream "
    "(tied to LIBOR/SOFR) on the same notional. The NPV is zero at inception when the fixed rate "
    "equals the **par swap rate** (fair rate)."
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("NPV ($)", f"${npv:,.0f}", help="Net present value from your perspective.")
k2.metric("Fair / Par Rate", f"{fair_rate*100:.4f}%", help="Fixed rate that makes NPV = 0 today.")
k3.metric("DV01 ($)", f"${dv01:,.0f}", help="$ change in NPV for a 1 bp parallel shift in rates.")
k4.metric("Tenor", f"{tenor} yrs", help="Remaining life of the swap.")

st.divider()

# NPV vs rate
rates = np.linspace(0.001, 0.15, 200)
npvs  = swap_npv_vs_rate(notional, fixed_rate, tenor, pay_fixed, rates)

fig = make_subplots(rows=1, cols=2, subplot_titles=("NPV vs Floating Rate", "Cash Flow Ladders"))

fig.add_trace(go.Scatter(
    x=rates * 100, y=npvs, name="NPV", line=dict(color="#1f77b4", width=2)
), row=1, col=1)
fig.add_hline(y=0, line_dash="dash", line_color="grey", row=1, col=1)
fig.add_vline(x=libor_pct, line_dash="dash", line_color="red",
    annotation_text="Current Rate", row=1, col=1)
fig.add_vline(x=fair_rate * 100, line_dash="dot", line_color="green",
    annotation_text="Par Rate", row=1, col=1)

# Cash flows
fixed_cfs  = [(cf.date().ISO(), -cf.amount() if pay_fixed else cf.amount())
              for cf in priced_swap.fixedLeg()]
float_cfs  = [(cf.date().ISO(), cf.amount() if pay_fixed else -cf.amount())
              for cf in priced_swap.floatingLeg()]
fig.add_trace(go.Bar(
    x=[d for d, _ in fixed_cfs], y=[a for _, a in fixed_cfs],
    name="Fixed Leg", marker_color="#d62728",
), row=1, col=2)
fig.add_trace(go.Bar(
    x=[d for d, _ in float_cfs], y=[a for _, a in float_cfs],
    name="Float Leg", marker_color="#2ca02c",
), row=1, col=2)
fig.update_layout(height=430, barmode="relative", template="plotly_white",
    legend=dict(orientation="h", y=-0.18))
fig.update_xaxes(title_text="Rate (%)", row=1, col=1)
fig.update_yaxes(title_text="NPV ($)", row=1, col=1)
fig.update_yaxes(title_text="Cash Flow ($)", row=1, col=2)
st.plotly_chart(fig, use_container_width=True)

# DV01 profile
st.subheader("DV01 Profile across Rate Levels")
dv01s = []
for r in rates:
    s1, _, _, _ = build_swap(notional, fixed_rate, tenor, pay_fixed)
    s2, _, _, _ = build_swap(notional, fixed_rate, tenor, pay_fixed)
    n1, _, _ = price_swap(s1, r)
    n2, _, _ = price_swap(s2, r + 0.0001)
    dv01s.append(n2 - n1)

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=rates * 100, y=dv01s, fill="tozeroy",
    line=dict(color="#9467bd"), name="DV01"))
fig2.add_vline(x=libor_pct, line_dash="dash", line_color="red", annotation_text="Current")
fig2.update_layout(height=350, template="plotly_white",
    xaxis_title="Rate (%)", yaxis_title="DV01 ($)")
st.plotly_chart(fig2, use_container_width=True)

with st.expander("📋 QuantLib Code — IRS Pricing"):
    st.code("""
import QuantLib as ql

today      = ql.Date.todaysDate()
ql.Settings.instance().evaluationDate = today
calendar   = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
settlement = calendar.advance(today, ql.Period(2, ql.Days))
maturity   = calendar.advance(settlement, ql.Period(5, ql.Years))

fixed_sch = ql.Schedule(settlement, maturity, ql.Period(ql.Semiannual), calendar,
    ql.ModifiedFollowing, ql.ModifiedFollowing, ql.DateGeneration.Forward, False)
float_sch = ql.Schedule(settlement, maturity, ql.Period(ql.Quarterly), calendar,
    ql.ModifiedFollowing, ql.ModifiedFollowing, ql.DateGeneration.Forward, False)

libor_rate  = 0.045
flat_curve  = ql.YieldTermStructureHandle(
    ql.FlatForward(today, libor_rate, ql.Actual360()))
index = ql.USDLibor(ql.Period(3, ql.Months), flat_curve)

swap = ql.VanillaSwap(
    ql.VanillaSwap.Payer, 10_000_000,
    fixed_sch, 0.04, ql.Thirty360(ql.Thirty360.BondBasis),
    float_sch, index, 0.0, ql.Actual360(),
)
swap.setPricingEngine(ql.DiscountingSwapEngine(flat_curve))

print(f"NPV       : {swap.NPV():,.2f}")
print(f"Fair Rate : {swap.fairRate()*100:.4f}%")
""", language="python")

with st.expander("📚 Key Concepts"):
    st.markdown("""
| Term | Meaning |
|---|---|
| **Payer swap** | You pay fixed, receive floating — profits when rates rise |
| **Receiver swap** | You receive fixed, pay floating — profits when rates fall |
| **Par / Fair rate** | The fixed rate that sets NPV = 0 at inception |
| **DV01** | Dollar value of a 1 basis-point move — the primary interest rate risk metric |
| **Notional** | Reference amount for calculating cash flows; not physically exchanged |
""")
