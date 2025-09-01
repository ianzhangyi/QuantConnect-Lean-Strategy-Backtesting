# Leveraged ETF Intraday Strategy

## Overview
This folder contains two **intraday leveraged ETF trading strategies** built on the **QuantConnect Lean (snake_case API)**.  
Both strategies use **signal assets** (SPY, NVDA, TLT) to generate trade signals, and execute trades on the corresponding **leveraged ETFs** (SPXL, NVDL, TMF).

- **Entry rule**: Buy when the signal asset trades below its daily open × `entry` threshold (default 0.995).  
- **Exit rule**: Close position when price reaches either stop-loss (`sl`, default 0.993) or take-profit (`tp`, default 1.015).  
- **Session**: Restricted to RTH (09:31–16:00).  
- **EOD**: Optional liquidation at 15:59 to avoid overnight risk.  

The main difference between the two versions is **position management**.

---

## Versions
- **V1** (`algorithm_v1.py`)  
  - Position sizing: ~1/6 of portfolio per trade.  
  - Multiple entries allowed per symbol (each day at most one entry, but multiple partial positions can coexist).  
  - Positions tracked in a list; each has its own entry price.

- **V2** (`algorithm_v2.py`)  
  - Position sizing: ~1/3 of portfolio per trade.  
  - Only one active position per symbol at a time.  
  - Flat requirement before re-entry.

---

## Parameters
Both versions support runtime parameters via the QuantConnect Web IDE **Parameters panel** or Lean CLI config:

| Parameter     | Default | Description                                    |
|---------------|---------|------------------------------------------------|
| `entry`       | 0.995   | Entry threshold (signal_price < open × entry) |
| `sl`          | 0.993   | Stop-loss multiple of entry price             |
| `tp`          | 1.015   | Take-profit multiple of entry price           |
| `target_pct`  | 1/6 (V1), 1/3 (V2) | Portfolio allocation per entry    |
| `eod_liq`     | true    | If true, liquidate all at 15:59               |

---

## Data & Universe
- **Signals**:  
  - SPY → SPXL  
  - NVDA → NVDL  
  - TLT → TMF  
- **Resolution**: Minute bars  
- **Open Reference**: Captured from the **09:30 bar OPEN** (via history at 09:31). If unavailable, fallback to current price.  

---

## Backtest Settings
- **Period**: 2024-01-01 to 2025-01-01  
- **Starting Cash**: \$100,000  
- **Brokerage Model**: InteractiveBrokers Cash (modifiable)  
- **Warmup**: 5 trading days to ensure indicators/data readiness  

---


## How to Run
### QuantConnect Web IDE
1. Create a new project.  
2. Copy either `algorithm_v1.py` or `algorithm_v2.py`.  
3. (Optional) Set parameters in **Parameters panel** (e.g., `entry=0.996, sl=0.992, tp=1.014`).  
4. Run backtest. Export charts/metrics into the `charts/` or `results/` folder.

### Lean CLI (optional, local)
- Provide a config JSON under `backtests/` with parameters.  
- Run `lean backtest backtests/leveraged_etf_intraday.json`.  
- Summarize results with scripts in `common/metrics.py` (if available).

---

## Notes & Risks
- Leveraged ETFs (SPXL, NVDL, TMF) suffer from **daily rebalancing drag** and **tracking error**, especially in volatile markets.  
- Signal underliers (SPY, NVDA, TLT) may have tighter spreads than leveraged ETFs, so **execution slippage** should be considered.  
- Fixed thresholds (0.995 / 0.993 / 1.015) are for demonstration. In production, conduct **parameter sweeps and out-of-sample tests**.  
- Always evaluate turnover, trading costs, and liquidity impact before applying to real capital.

---

## Suggested Extensions
- Add more symbols or sectors for diversification.  
- Explore **alternative entry conditions** (e.g., VWAP deviation, volatility filters).  
- Integrate **risk models** from `common/risk.py` (max drawdown cap, trailing stops).  
- Automate **parameter grid testing** and export results into a summary CSV/heatmap.
