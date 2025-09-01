# Gap Breakout + Volume + Yesterday RSI

## Strategy Summary
This strategy trades a **daily gap-up breakout** with **volume confirmation** and a **momentum filter** based on **yesterday's RSI**.

- **Universe**: Top `N` liquid stocks by dollar volume with price `> $10` (coarse selection; daily resolution).
- **Entry (near close)**:
  1. **Gap-up**: `today_open > yesterday_high`
  2. **Breakout**: `today_close > max(close[-lookback_days:])`
  3. **Volume confirm**: `today_volume > mean(volume[-volume_ma_days:])`
  4. **Momentum filter**: `RSI_yesterday > 50`
- **Exit**: **Time-based** holding for `holding_days` (equal weight across positions, max `max_positions`).

> RSI uses a daily indicator with a 2-length rolling window so that **index 1** is “yesterday’s RSI”.

---

## Parameters
These can be overridden in the **QuantConnect Parameters** panel or Lean CLI config:

| Name             | Default | Description                                  |
|------------------|--------:|----------------------------------------------|
| `lookback_days`  | 20      | Breakout lookback window                     |
| `volume_ma_days` | 10      | Volume moving-average window                 |
| `holding_days`   | 10      | Holding period (calendar days)               |
| `max_positions`  | 10      | Max concurrent positions                     |
| `rsi_period`     | 14      | RSI period (Wilder)                          |
| `universe_count` | 100     | Top N by dollar volume                       |
| `min_price`      | 10      | Minimum price filter                         |

---

## Data & Universe
- **Resolution**: Daily  
- **Universe Construction**: Coarse selection by dollar volume + price filter.  
- **Indicator**: Daily RSI stored in a `RollingWindow(2)`; `window[1]` is yesterday's RSI for momentum gating.

---

## Backtest Settings (example)
- **Period**: 2024-06-01 → 2025-01-01  
- **Starting Cash**: \$100,000  
- **Rebalance/Execution**: Signals evaluated ~10 minutes before the close; orders are placed in `on_data`.

---

## How to Run (QuantConnect Web IDE)
1. Create a new project and paste `algorithm.py`.  
2. (Optional) Set parameters, e.g.  
   - `lookback_days=20, volume_ma_days=10, holding_days=10, max_positions=10`  
3. Run backtest. Export a summary table and a few equity curve/turnover charts to your repo’s `results/` / `charts/` folders.

---

## Notes & Extensions
- **Robustness**: Consider adding delistings/ETF blacklist filters, minimum dollar volume by day, ADR exclusion, etc.  
- **Risk**: Add stop-loss / take-profit, or a trailing stop model instead of pure time-based exit.  
- **Bias control**: To reduce look-ahead, compute all conditions using **yesterday** info except `today_open` and `today_close` as specified.  
- **Evaluation**: Report `CAGR, Sharpe, MaxDD, Hit Ratio, Avg Win/Loss, Turnover`. Perform **parameter sweeps** for stability.  
- **Universe dynamics**: Coarse runs daily; signals are computed with daily bars. You may also integrate a Fine selection for fundamentals.

