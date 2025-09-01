# quantconnect-strategy-backtesting

## Overview
This repository collects multiple **QuantConnect Lean (new snake_case API)** strategies for backtesting and research.  
Each strategy lives in its own folder with:
- `algorithm.py` (main strategy code)
- `README.md` (strategy logic, parameters, metrics, how to run)
- `params.json` (optional default parameters)
- `results/` (small CSV/JSON summaries) and `charts/` (exported plots)

> Why monorepo: shared utilities, consistent metrics and conventions, easier maintenance.  
> For resume: pin this repo and optionally break out your top strategy into a separate “showcase” repo.

---

## Repository Structure
```
quantconnect-strategy-backtesting/
├── strategies/
│   ├── leveraged_etf_intraday/
│   │   ├── algorithm.py
│   │   ├── README.md
│   │   ├── params.json
│   │   ├── results/           # small CSV/JSON summaries only
│   │   └── charts/            # small PNGs only
│   ├── gap_breakout_equities/
│   │   ├── algorithm.py
│   │   ├── README.md
│   │   ├── params.json
│   │   ├── results/
│   │   └── charts/
│   └── mean_reversion_pair/
│       ├── algorithm.py
│       ├── README.md
│       ├── params.json
│       ├── results/
│       └── charts/
├── common/                    # shared utils (optional)
│   ├── metrics.py             # unified metrics, JSON/CSV writer
│   ├── risk.py                # reusable risk models/helpers
│   └── utils.py               # time/session/helper functions
├── research/                  # notebooks for exploration (optional)
│   └── leveraged_etf_intraday.ipynb
├── backtests/                 # Lean CLI configs or batch scripts (optional)
│   ├── leveraged_etf_intraday.json
│   ├── gap_breakout_equities.json
│   └── run_all.sh
├── README.md                  # (this file) top-level overview + index
├── requirements.txt           # for research/plots only (Lean runtime not required)
└── .gitignore
```

---

## Strategy Index
| Strategy | Folder | Core Idea | Universe | Exit | Notes |
|---|---|---|---|---|---|
| Leveraged ETF Intraday | `strategies/leveraged_etf_intraday` | Open-pullback entry + TP/SL; trade leveraged ETFs using underlier signals | SPXL/NVDL/TMF (signals: SPY/NVDA/TLT) | ±1.5% / −0.7% & EOD | two modes: multi-entry / single-position |
| Gap Breakout (Equities) | `strategies/gap_breakout_equities` | Gap + N-day breakout filter | S&P500 | T+1 or TP/SL | daily/minute versions |
| Mean Reversion Pair | `strategies/mean_reversion_pair` | Spread reversion with bands | curated pairs | band exit | risk parity sizing |

---

## Conventions
- **Lean API**: new snake_case (e.g., `initialize`, `on_data`, `set_start_date`).
- **Trading session**: restrict to RTH; schedule EOD liquidation at 15:59 if strategy requires.
- **Costs**: set brokerage/fees/slippage consistently across strategies.
- **Metrics**: report *at least* `CAGR, Sharpe, MaxDD, HitRatio, AvgWin, AvgLoss, Turnover`.  
  Use `common/metrics.py` to ensure comparable outputs.
- **Artifacts**: keep `results/` and `charts/` **small**. Prefer CSV/JSON summaries and compressed PNGs.
- **.gitignore**: do not commit large raw data or full backtest blobs.

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

