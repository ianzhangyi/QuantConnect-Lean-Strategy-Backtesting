# Leveraged ETF Intraday

## Strategy Summary
- **Signal vs Trade**: use underliers (SPY/NVDA/TLT) as signals; **trade** leveraged ETFs (SPXL/NVDL/TMF).
- **Entry**: intraday signal price < **open × 0.995**.
- **Exit**: take-profit at **1.015 × entry** or stop-loss at **0.993 × entry**.
- **Session**: trade only during regular hours (09:30–16:00).  
- **EOD**: (Optional) You may add 15:59 liquidation scheduling if desired.

## Versions
- **V1** (`algorithm_v1.py`)  
  - Each entry uses ~**1/6** of portfolio.  
  - **Multiple entries** per symbol allowed.
- **V2** (`algorithm_v2.py`)  
  - Each entry uses ~**1/3** of portfolio.  
  - **Single position** per symbol (no multiple entries on the same day).

## Universe
- **Signals**: SPY, NVDA, TLT (minute bars).  
- **Traded**: SPXL, NVDL, TMF (minute bars).

## How to Run (QuantConnect Web IDE)
1. Create a new project; upload either `algorithm_v1.py` or `algorithm_v2.py`.
2. Set **Start** = `2024-01-01`, **End** = `2025-01-01`, **Cash** = `100000` (already in code; adjust as needed).
3. Run backtest and review logs/plots.  
   - V1 will allow multiple partial positions per symbol.  
   - V2 will only keep one active position per symbol.

## Notes / Risks
- Leveraged ETFs (SPXL/NVDL/TMF) have **rebalancing drag** and **tracking error**, performance can deviate from underliers.
- The signal uses **underlier prices**; orders are placed on **leveraged ETFs**. Liquidity/slippage may differ.
- Thresholds (0.995 / 0.993 / 1.015) are **fixed** here; consider parameter sweeps and **out-of-sample** validation before drawing conclusions.
- For more realistic fills/costs, consider setting brokerage/fee/slippage models and EOD liquidation.

## Suggested Extensions
- Add **EOD liquidation** at 15:59 via `self.schedule.on(self.date_rules.every_day(), self.time_rules.at(15, 59), self.liquidate)`.
- Parameterize thresholds and position sizes using `self.get_parameter('entry')` etc. for grid tests.
- Export backtest metrics (CAGR, Sharpe, Max DD, Hit ratio, Avg win/loss, Turnover) to `results/`.

