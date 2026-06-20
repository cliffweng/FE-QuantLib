# QuantLib Educational App

## Stack
- Python 3.13 + QuantLib 1.42 + Streamlit 1.54 + Plotly 6.5

## Run
```
streamlit run src/app.py
```

## Structure
- `src/app.py` — home page and navigation
- `src/pages/` — one file per instrument (bonds, options, swaps, yield curve, FX forwards)
- `tests/` — unit tests for pricing logic

## Conventions
- Each page: sidebar controls → main panel with chart + explanation + code snippet
- Use `st.expander` for code snippets and math
- Pricing logic lives in module-level functions so tests can import them
