from AlgorithmImports import *

class LeveragedETFIntradayV2(QCAlgorithm):
    """
    Version 2 (single-position per symbol):
    - Signals from underliers (SPY/NVDA/TLT), trade leveraged ETFs (SPXL/NVDL/TMF)
    - Entry   : signal_price < open_ref * entry (default 0.995)
    - Exit    : take-profit at tp (1.015×entry_price) or stop-loss at sl (0.993×entry_price)
    - Sizing  : each fill ~ target_pct (default 1/3), only one active position per symbol
    - RTH only; optional EOD liquidation (15:59)
    - New Lean snake_case API
    """

    def initialize(self):
        # ---- Parameters ----
        self.entry = float(self.get_parameter("entry") or 0.995)
        self.sl    = float(self.get_parameter("sl")    or 0.993)
        self.tp    = float(self.get_parameter("tp")    or 1.015)
        self.target_pct = float(self.get_parameter("target_pct") or (1.0/3.0))
        self.use_eod_liq = (self.get_parameter("eod_liq") or "true").lower() == "true"

        # ---- Dates & Cash ----
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2025, 1, 1)
        self.set_cash(100000)

        self.set_brokerage_model(BrokerageName.INTERACTIVE_BROKERS, AccountType.CASH)

        # ---- Universe ----
        mapping = {"SPXL": "SPY", "NVDL": "NVDA", "TMF": "TLT"}
        self.signal_assets, self.trade_assets = {}, {}
        for etf, underlier in mapping.items():
            sig = self.add_equity(underlier, Resolution.MINUTE).symbol
            tra = self.add_equity(etf,       Resolution.MINUTE).symbol
            self.signal_assets[etf] = sig
            self.trade_assets[etf]  = tra

        # ---- State ----
        self.open_ref = {sig: None for sig in self.signal_assets.values()}
        self.last_trade_date = {tra: None for tra in self.trade_assets.values()}
        # single active position per traded symbol: dict or None
        self.position = {tra: None for tra in self.trade_assets.values()}

        self.set_warmup(timedelta(days=5))

        # capture open at 09:31
        for etf, sig in self.signal_assets.items():
            self.schedule.on(
                self.date_rules.every_day(sig),
                self.time_rules.at(9, 31),
                self._make_open_capture(sig)
            )

        if self.use_eod_liq:
            self.schedule.on(
                self.date_rules.every_day(),
                self.time_rules.at(15, 59),
                self._eod_liquidate
            )

    def _make_open_capture(self, signal_symbol: Symbol):
        def _cb():
            day = self.time.date()
            open_px = None
            try:
                hist = self.history(signal_symbol, 40, Resolution.MINUTE)
                if not hist.empty and 'open' in hist.columns:
                    for ts, row in hist.iterrows():
                        tstamp = ts[1] if isinstance(ts, tuple) else ts
                        if tstamp.date() == day and tstamp.hour == 9 and tstamp.minute == 30:
                            open_px = float(row["open"])
                            break
            except Exception as e:
                self.debug(f"[open_capture] history error for {signal_symbol.Value}: {e}")
            if open_px is None:
                open_px = self.securities[signal_symbol].price
            self.open_ref[signal_symbol] = open_px
            for etf, sig in self.signal_assets.items():
                if sig == signal_symbol:
                    tra = self.trade_assets[etf]
                    self.last_trade_date[tra] = None
            self.debug(f"[open_capture] {signal_symbol.Value} open_ref={open_px:.4f} at {self.time}")
        return _cb

    def _eod_liquidate(self):
        for etf, tra in self.trade_assets.items():
            if self.portfolio[tra].invested:
                self.liquidate(tra)
            self.position[tra] = None
        self.debug(f"[EOD] Liquidated all at {self.time}")

    def on_data(self, data: Slice):
        if self.time.hour < 9 or (self.time.hour == 9 and self.time.minute < 31) or self.time.hour >= 16:
            return

        current_date = self.time.date()

        for etf, sig in self.signal_assets.items():
            tra = self.trade_assets[etf]

            if self.open_ref[sig] is None:
                continue
            if sig not in data or data[sig] is None:
                continue
            if not self.securities[tra].is_tradable:
                continue

            px = data[sig].price

            # exit if we have an active position
            pos = self.position[tra]
            if pos is not None:
                entry = pos["entry"]; qty = pos["qty"]
                if px <= entry * self.sl or px >= entry * self.tp:
                    self.market_order(tra, -qty)
                    self.position[tra] = None

            # entry only if flat AND not traded yet today
            if (self.last_trade_date[tra] != current_date and
                self.position[tra] is None and
                px < self.open_ref[sig] * self.entry):
                qty = self.calculate_order_quantity(tra, self.target_pct)
                if qty != 0:
                    self.market_order(tra, qty)
                    self.position[tra] = {"entry": px, "qty": qty}
                    self.last_trade_date[tra] = current_date

    def on_order_event(self, order_event: OrderEvent):
        if order_event.status == OrderStatus.FILLED:
            order = self.transactions.get_order_by_id(order_event.order_id)
            self.log(
                f"TRADE | {self.time} | {order.symbol.Value} | "
                f"{'BUY' if order.direction == OrderDirection.BUY else 'SELL'} | "
                f"Qty: {order_event.fill_quantity} | Price: {order_event.fill_price:.4f}"
            )
