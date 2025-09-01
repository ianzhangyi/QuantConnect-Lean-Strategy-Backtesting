# QuantConnect-strategy-backtesting

## Overview
This repository collects multiple **QuantConnect Lean** strategies for backtesting and research.  
Each strategy lives in its own folder with:
- `algorithm.py` (main strategy code)
- `README.md` (strategy logic, parameters, metrics, how to run)
- `params.json` (optional default parameters)
- `results/` (small CSV/JSON summaries) and `charts/` (exported plots)
---

## Strategy Index
| Strategy | Folder | Core Idea | Universe | Exit | Notes |
|---|---|---|---|---|---|
| Leveraged ETF Intraday | `strategies/leveraged_etf_intraday` | Open-pullback entry + TP/SL; trade leveraged ETFs using underlier signals | SPXL/NVDL/TMF (signals: SPY/NVDA/TLT) | ±1.5% / −0.7% & EOD | two modes: multi-entry / single-position |
| Gap Breakout (Equities) | `strategies/gap_breakout_equities` | Gap + N-day breakout filter | S&P500 Components | T+1 or TP/SL | daily/minute versions |


---

## Conventions
- **Lean API**: new snake_case (e.g., `initialize`, `on_data`, `set_start_date`).
- **Trading session**: restrict to RTH; schedule EOD liquidation at 15:59 if strategy requires.
- **Costs**: set brokerage/fees/slippage consistently across strategies.
- **Metrics**: report *at least* `CAGR, Sharpe, MaxDD, HitRatio, AvgWin, AvgLoss, Turnover`.  
  Use `common/metrics.py` to ensure comparable outputs.
- **Artifacts**: keep `results/` and `charts/` **small**. Prefer CSV/JSON summaries and compressed PNGs.


---

## How to Run
### A) QuantConnect Web IDE
- Upload the `algorithm.py` from a strategy folder.
- (Optional) Set **Parameters** in the IDE (e.g., `version=1`, `entry=0.995`, `sl=0.993`, `tp=1.015`).
- Run backtest and export summary numbers/screenshots to `results/` and `charts/`.

### B) Lean CLI (optional, local)
- Place a config JSON under `backtests/strategy_name.json`.
- Run `lean backtest backtests/strategy_name.json` (adjust per your local setup).
- Post-process results via `common/metrics.py`.

---

