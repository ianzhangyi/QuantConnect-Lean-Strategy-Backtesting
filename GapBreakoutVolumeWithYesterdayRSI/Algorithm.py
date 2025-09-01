from AlgorithmImports import *
from QuantConnect.Indicators import RollingWindow

class GapBreakoutVolumeWithYesterdayRSI(QCAlgorithm):
    """
    Gap + Breakout + Volume confirmation + Yesterday's RSI filter
    Universe: top liquid names by dollar volume (price > 10), Daily resolution
    Entry:    Gap-up (open > yday high) and Close > N-day highest close, Volume > M-day avg volume, RSI_yesterday > 50
    Exit:     Time-based hold for H days (equal-weight, up to K concurrent positions)
    """

    def initialize(self):
        # ---- parameters (overridable in QC Parameters panel) ----
        self.lookback_days   = int(self.get_parameter("lookback_days")   or 20)   # breakout lookback
        self.volume_ma_days  = int(self.get_parameter("volume_ma_days")  or 10)   # volume MA window
        self.holding_days    = int(self.get_parameter("holding_days")    or 10)   # holding period (calendar days)
        self.max_positions   = int(self.get_parameter("max_positions")   or 10)   # concurrent holdings
        self.rsi_period      = int(self.get_parameter("rsi_period")      or 14)   # RSI period
        self.universe_count  = int(self.get_parameter("universe_count")  or 100)  # top N by dollar volume
        self.min_price       = float(self.get_parameter("min_price")     or 10)   # min price filter

        # ---- backtest setup ----
        self.set_start_date(2024, 6, 1)
        self.set_end_date(2025, 1, 1)
        self.set_cash(100000)

        # Daily universe
        self.universe_settings.resolution = Resolution.DAILY
        self.add_universe(self.coarse_selection_function)

        # state
        self.symbol_data: dict[Symbol, SymbolData] = {}
        self.active_positions: dict[Symbol, datetime] = {}  # entry time per symbol
        self.daily_universe: set[Symbol] = set()            # updated each day by coarse

        # run selection step ~10 min before close so "today bar" exists
        self.schedule.on(
            self.date_rules.every_day(),
            self.time_rules.before_market_close("SPY", 10),
            self.selection_step
        )

    # ----------------- UNIVERSE SELECTION -----------------
    def coarse_selection_function(self, coarse: List[CoarseFundamental]) -> List[Symbol]:
        # filter: has fundamental, tradable price
        filtered = [c for c in coarse if c.has_fundamental_data and c.price is not None and c.price > self.min_price]
        # sort by dollar volume desc and take top N
        selected = sorted(filtered, key=lambda x: x.dollar_volume or 0, reverse=True)[:self.universe_count]
        symbols = [c.symbol for c in selected]
        # cache universe for the day
        self.daily_universe = set(symbols)
        return symbols

    # ----------------- DAILY SELECTION LOGIC -----------------
    def selection_step(self):
        """
        Compute today's selection list near the close using daily bars & indicators.
        """
        self.filtered: list[Symbol] = []

        # iterate over today's universe only
        for symbol in list(self.daily_universe):
            try:
                # ensure SymbolData exists
                sd = self.symbol_data.get(symbol)
                if sd is None:
                    sd = SymbolData(self, symbol, self.rsi_period)
                    self.symbol_data[symbol] = sd

                # update RSI rolling window (stores "today" at index 0, "yesterday" at index 1)
                sd.update()
                if not sd.is_ready():
                    continue

                # pull enough daily history so that we have [lookback_days] + yesterday + today
                bars_needed = self.lookback_days + 2
                hist = self.history(symbol, bars_needed, Resolution.DAILY)
                if hist is None or hist.empty or len(hist) < bars_needed:
                    continue

                # QC daily history here is typically indexed by time only (for single symbol)
                # Ensure required fields exist
                for col in ("open", "high", "close", "volume"):
                    if col not in hist.columns:
                        raise ValueError(f"history missing column: {col}")

                # last two rows are yesterday & today
                yesterday = hist.iloc[-2]
                today     = hist.iloc[-1]

                closes  = hist["close"].iloc[: -1]  # up to yesterday
                highs   = hist["high"].iloc[: -1]   # up to yesterday (for context)
                volumes = hist["volume"].iloc[: -1] # up to yesterday

                # conditions
                gap_up        = today["open"] > yesterday["high"]
                breakout_lvl  = closes.iloc[-self.lookback_days:].max()  # highest close in lookback (excluding today)
                breakout      = today["close"] > breakout_lvl
                vol_ma        = volumes.iloc[-self.volume_ma_days:].mean()
                volume_confirm= today["volume"] > vol_ma
                rsi_yesterday = sd.rsi_window[1].value  # yesterday's RSI
                rsi_confirm   = rsi_yesterday > 50

                if gap_up and breakout and volume_confirm and rsi_confirm:
                    self.filtered.append(symbol)

            except Exception as e:
                self.debug(f"[selection_step] {symbol.Value}: {e}")
                continue

    # ----------------- EXECUTION -----------------
    def on_data(self, data: Slice):
        # entries
        for symbol in getattr(self, "filtered", []):
            if symbol not in self.daily_universe:
                continue
            if symbol in self.active_positions:
                continue
            if len(self.active_positions) >= self.max_positions:
                break
            # ensure tradable
            if symbol not in self.securities or not self.securities[symbol].is_tradable:
                continue

            # equal weight
            target = 1.0 / max(1, self.max_positions)
            self.set_holdings(symbol, target)
            self.active_positions[symbol] = self.time
            self.log(f"BUY  {symbol.Value} | px={self.securities[symbol].price:.2f} | date={self.time.date()}")

        # exits (time-based)
        to_exit = []
        for symbol, entry_time in self.active_positions.items():
            if (self.time - entry_time).days >= self.holding_days:
                to_exit.append(symbol)

        for symbol in to_exit:
            if symbol in self.securities and self.securities[symbol].is_tradable:
                self.liquidate(symbol)
                self.log(f"SELL {symbol.Value} | px={self.securities[symbol].price:.2f} | date={self.time.date()}")
            self.active_positions.pop(symbol, None)


class SymbolData:
    """
    Per-symbol indicator container: Daily RSI with a RollingWindow(2) to access "yesterday" value at index 1.
    """
    def __init__(self, algorithm: QCAlgorithm, symbol: Symbol, rsi_period: int):
        self.symbol = symbol
        self.algorithm = algorithm
        # Daily RSI (Wilder)
        self.rsi = algorithm.rsi(symbol, rsi_period, MovingAverageType.WILDERS, Resolution.DAILY)
        # Rolling window to store [today, yesterday]
        self.rsi_window: RollingWindow

    def update(self):
        # push today's RSI into window when ready
        if self.rsi.is_ready:
            self.rsi_window.add(self.rsi.current)

    def is_ready(self) -> bool:
        return self.rsi_window.is_ready
