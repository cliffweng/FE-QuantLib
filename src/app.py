import streamlit as st

st.set_page_config(
    page_title="QuantLib Explorer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 QuantLib Financial Instruments Explorer")
st.markdown(
    """
Welcome! This interactive app demonstrates how to use **[QuantLib](https://www.quantlib.org/)**
— the open-source library for quantitative finance — to price a range of financial instruments.

Select a topic from the sidebar to get started.
"""
)

col1, col2, col3 = st.columns(3)
cards = [
    ("🏦", "Bonds", "pages/1_bonds.py", "Price fixed-rate bonds, compute YTM, duration & convexity, and visualise price-yield curves."),
    ("📊", "Options (Black-Scholes)", "pages/2_options.py", "Price European & American options, explore Greeks, and visualise the volatility surface."),
    ("🔄", "Interest Rate Swaps", "pages/3_swaps.py", "Build a vanilla IRS, compute NPV and DV01 across different rate environments."),
    ("📐", "Yield Curve", "pages/4_yield_curve.py", "Bootstrap a yield curve from deposit and swap rates and explore forward / zero rates."),
    ("💱", "FX Forwards", "pages/5_fx_forwards.py", "Price FX forward contracts using covered interest rate parity."),
]
cols = [col1, col2, col3, col1, col2]
for (icon, title, _, desc), col in zip(cards, cols):
    with col:
        st.info(f"**{icon} {title}**\n\n{desc}")

st.divider()
st.markdown(
    """
### How this app is built
Each page follows the same pattern:
1. **Sidebar** — adjust instrument parameters with sliders and inputs
2. **Chart** — interactive Plotly visualisation that updates live
3. **Explanation** — the finance intuition behind the numbers
4. **Code snippet** — the exact QuantLib Python code used, ready to copy

> QuantLib version in use: `QuantLib {}`
""".format(__import__("QuantLib").__version__)
)

st.divider()
st.markdown(
    """
### Built with
| Library | Role |
|---|---|
| [QuantLib](https://www.quantlib.org/) | Pricing engine — bonds, options, swaps, yield curves, FX forwards |
| [Streamlit](https://streamlit.io/) | Interactive web UI and parameter controls |
| [Plotly](https://plotly.com/python/) | Interactive charts and 3-D surfaces |
| [pandas](https://pandas.pydata.org/) | Tabular data and scenario tables |
| [NumPy](https://numpy.org/) | Numerical arrays and sensitivity sweeps |

**QuantLib** is an open-source C++ library for quantitative finance, with Python bindings via SWIG.
It is maintained by the [QuantLib community](https://github.com/lballabio/QuantLib) and released under the BSD license.

**Streamlit** is an open-source Python framework for building data apps, maintained by [Snowflake](https://streamlit.io/) and released under the Apache 2.0 license.

---
Built by **[Cliff Weng](https://github.com/cliffweng)**

*If you use or adapt this app, please credit [Cliff Weng](https://github.com/cliffweng) and link back to the original repository.*
"""
)
