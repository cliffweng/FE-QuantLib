# QuantLib Financial Instruments Explorer

An interactive educational app built with **QuantLib** and **Streamlit** that demonstrates how to price common financial instruments, visualise their sensitivities, and understand the maths behind them — all in a live, parameter-driven UI.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![QuantLib](https://img.shields.io/badge/QuantLib-1.42-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.54-red)

## Instruments covered

| Page | What you learn |
|---|---|
| **Bonds** | Fixed-rate bond pricing, YTM, modified duration, convexity, price-yield curve, cash flow schedule |
| **Options (Black-Scholes)** | European & American vanilla options, all 6 Greeks, payoff diagram, 3-D volatility surface |
| **Interest Rate Swaps** | Vanilla IRS NPV, par/fair rate, DV01, NPV vs rate curve, fixed & floating cash flow ladders |
| **Yield Curve** | Bootstrapping from deposit + swap rates, zero rates, forward rates, discount factors |
| **FX Forwards** | Covered interest rate parity pricing, forward points, premium/discount, rate-differential surface |

Each page follows the same pattern:
- **Sidebar sliders** — adjust every parameter and see results update instantly
- **Plotly charts** — interactive, zoomable, hoverable
- **Concept explanations** — the finance intuition and the maths (LaTeX rendered)
- **QuantLib code snippet** — copy-paste ready Python using the exact same code that powers the page
- **Sensitivity tables** — scenario analysis across rate shifts and spot moves

## Setup

```bash
# 1. Clone
git clone <repo-url>
cd FE-QuantLib

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
streamlit run src/app.py
```

App opens at `http://localhost:8501`.

## Requirements

```
QuantLib>=1.42
streamlit>=1.54
plotly>=6.5
pandas>=2.0
numpy>=1.26
```

## Project structure

```
FE-QuantLib/
├── src/
│   ├── app.py                  # Home page and navigation
│   └── pages/
│       ├── 1_bonds.py          # Fixed-rate bond pricing
│       ├── 2_options.py        # Black-Scholes / finite-difference options
│       ├── 3_swaps.py          # Vanilla interest rate swap
│       ├── 4_yield_curve.py    # Yield curve bootstrapping
│       └── 5_fx_forwards.py    # FX forward pricing
├── tests/                      # Unit tests for pricing logic
├── requirements.txt
└── CLAUDE.md
```

## Implementation notes

- **Bond prices** — QuantLib returns clean price per 100 of face; the app scales to actual dollar amounts.
- **Options** — European options use `AnalyticEuropeanEngine` (closed-form BSM). American options use `FdBlackScholesVanillaEngine` (Crank-Nicolson finite difference).
- **Swaps** — Uses a synthetic `IborIndex` with 0 fixing-day lag so all coupons are projected from the forward curve without requiring historical fixings.
- **Yield curve** — Bootstrapped with `PiecewiseLogCubicDiscount` interpolation for a smooth, arbitrage-free curve.
- **FX forwards** — Priced analytically via `F = S · DF_foreign / DF_domestic` (covered interest rate parity).
