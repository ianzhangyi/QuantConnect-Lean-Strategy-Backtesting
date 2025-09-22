from AlgorithmImports import *
from datetime import datetime, timedelta
from collections import deque

RAW_URL = "https://raw.githubusercontent.com/ianzhangyi/QuantConnect-Lean-Strategy-Backtesting/main/QQQ_sentiment_signal_analysis/signals.csv"

# —— 自定义 signal，当天可用（不滞后） ——
class signal_csv(PythonData):
    def get_source(self, config, date, is_live_mode):
        return SubscriptionDataSource(RAW_URL, SubscriptionTransportMedium.REMOTE_FILE)

    def reader(self, config, line, date, is_live_mode):
        if not line or "date" in line.lower():
            return None
        try:
            d, sig = [p.strip() for p in line.split(",")[:2]]
            obj = signal_csv()
            obj.symbol   = config.symbol
            obj.time     = datetime.strptime(d, "%Y-%m-%d")
            obj.end_time = obj.time           
            sig = float(sig)
            obj.value    = sig
            obj["signal"]= sig
            return obj
        except Exception:
            return None


class qqq_long_short_on_signals(QCAlgorithm):

    def initialize(self):
        # 回测区间 / 初始资金
        self.set_start_date(2010, 1, 6)
        self.set_end_date(2025, 8, 27)
        self.set_cash(100000)

        # 参数：卖出阈值与SMA长度可调
        self.sell_threshold = float(self.get_parameter("sell_threshold", 2.5))   # 触发做空的 signal 阈值
        self.sma_length     = int(self.get_parameter("sma_length", 30))         # VIX ratio 的均线长度

        # 订阅标的与数据
        self.qqq = self.add_equity("QQQ", Resolution.MINUTE).symbol
        self.sig_symbol = self.add_data(signal_csv, "QQQ", Resolution.DAILY).symbol
        self.vix   = self.add_data(CBOE, "VIX",   Resolution.DAILY).symbol
        self.vx3m  = self.add_data(CBOE, "VIX3M", Resolution.DAILY).symbol

        # 合成日线（用于在收盘决策）
        self.daily_con = TradeBarConsolidator(timedelta(days=1))
        self.daily_con.data_consolidated += self.on_daily_bar
        self.subscription_manager.add_consolidator(self.qqq, self.daily_con)

        self.vix_con = TradeBarConsolidator(timedelta(days=1))
        self.vix_con.data_consolidated += self.on_vix_bar
        self.subscription_manager.add_consolidator(self.vix, self.vix_con)

        self.vx3m_con = TradeBarConsolidator(timedelta(days=1))
        self.vx3m_con.data_consolidated += self.on_vx3m_bar
        self.subscription_manager.add_consolidator(self.vx3m, self.vx3m_con)

        # 预热：给 VIX ratio 与 SMA 初始化窗口
        self.set_warmup(timedelta(days=max(60, self.sma_length)), Resolution.DAILY)

        # 状态与缓存
        self.signal_today    = None
        self.signal_yest     = None
        self.ref_close_today = None

        self.last_vix_close  = None
        self.last_vx3m_close = None
        self.ratio_last      = None
        self.ratio_window    = deque(maxlen=self.sma_length)
        self.sma_last        = None

        # 计划：('long'|'short', ref_close, s_prev, ratio_prev, sma_prev)
        self.next_day_action = None

        # 首次开盘先全仓做多
        self.did_initial_buy = False

        # 当前方向：+1 多 / -1 空 / 0 空仓（正式运行后基本在 ±1 之间）
        self.side = 0

        # 统计
        self.long_entries  = 0
        self.short_entries = 0

        # 调度：次日开盘前 1 分钟下 MOO
        self.schedule.on(
            self.date_rules.every_day(self.qqq),
            self.time_rules.before_market_open(self.qqq, 1),
            self.preopen_execute
        )

    # 小工具
    def _fmt(self, x, d=3): return "na" if x is None else f"{x:.{d}f}"

    # 读取当日 signal
    def on_data(self, slice: Slice):
        if slice.contains_key(self.sig_symbol):
            self.signal_today = float(slice[self.sig_symbol].value)
            if not hasattr(self, "_sig_once"):
                self.debug(f"signal example: {self.signal_today:.3f} at {self.time}")
                self._sig_once = True

    # VIX / VIX3M 更新
    def on_vix_bar(self, sender, bar: TradeBar):
        self.last_vix_close = bar.close
        self._update_ratio()

    def on_vx3m_bar(self, sender, bar: TradeBar):
        self.last_vx3m_close = bar.close
        self._update_ratio()

    def _update_ratio(self):
        if self.last_vix_close is None or self.last_vx3m_close in (None, 0):
            return
        ratio = self.last_vix_close / self.last_vx3m_close
        self.ratio_last = ratio
        self.ratio_window.append(ratio)
        if len(self.ratio_window) == self.ratio_window.maxlen:
            self.sma_last = sum(self.ratio_window) / len(self.ratio_window)

    # 收盘：根据当日数据决定次日方向（多/空）
    def on_daily_bar(self, sender, bar: TradeBar):
        if self.is_warming_up:
            self.next_day_action = None
            self.ref_close_today = None
            return

        self.ref_close_today = bar.close
        s     = self.signal_today
        ratio = self.ratio_last
        sma   = self.sma_last

        if s is None or ratio is None or sma is None:
            self.next_day_action = None
            return

        # —— 方向判定 —— 
        # 做空条件（反手/建空）：signal >= 阈值 且 ratio > SMA
        want_short = (s >= self.sell_threshold) and (ratio > sma)

        # 做多条件（反手/建多）：signal < 0 且 ratio < SMA
        want_long  = (s < 0.0) and (ratio < sma)

        plan = None
        if want_short and self.side != -1:
            plan = 'short'
        elif want_long and self.side != +1:
            plan = 'long'

        self.next_day_action = (plan, self.ref_close_today, s, ratio, sma) if plan else None
        self.signal_yest = s

    # 次日开盘：按计划用 MOO 切换到目标方向（全仓）
    def preopen_execute(self):
        if self.is_warming_up:
            return

        # 基线：首个可交易日全仓做多一次
        if not self.did_initial_buy:
            price = self.securities[self.qqq].price
            if price and price > 0:
                shares = int(self.portfolio.total_portfolio_value / price)
                if shares > 0:
                    self.market_on_open_order(self.qqq, shares)
                    self.side = +1
                    self.long_entries += 1
                    self.debug(f"BASELINE LONG | date={self.time.date()} | est_open_px={self._fmt(price,2)} | shares={shares}")
                    self.did_initial_buy = True
            return

        if self.next_day_action is None:
            return

        plan, ref_close, s_prev, ratio_prev, sma_prev = self.next_day_action

        price = ref_close if ref_close and ref_close > 0 else self.securities[self.qqq].price
        if not price or price <= 0:
            self.next_day_action = None
            return

        target_value  = self.portfolio.total_portfolio_value
        target_shares = int(target_value / price)

        cur_qty   = self.portfolio[self.qqq].quantity
        qty_delta = 0

        if plan == 'long':
            # 切到全仓多：目标 = +target_shares
            qty_delta = max(0, target_shares) - cur_qty
        elif plan == 'short':
            # 切到全仓空：目标 = -target_shares
            qty_delta = -max(0, target_shares) - cur_qty

        if qty_delta != 0:
            self.market_on_open_order(self.qqq, qty_delta)

            # 日志
            self.debug(
                f"ENTRY {plan.upper()} | date={self.time.date()} | "
                f"signal(prev)={self._fmt(s_prev,3)} | vix_ratio(prev)={self._fmt(ratio_prev,4)} | sma(prev)={self._fmt(sma_prev,4)} | "
                f"ref_close={self._fmt(ref_close,2)} | est_open_px={self._fmt(price,2)} | qty_delta={qty_delta}"
            )

            # 状态/计数
            if plan == 'long' and self.side != +1:
                self.long_entries += 1
                self.side = +1
            elif plan == 'short' and self.side != -1:
                self.short_entries += 1
                self.side = -1

        self.next_day_action = None

    def on_end_of_algorithm(self):
        self.debug(f"Finished. long_entries={self.long_entries}, short_entries={self.short_entries}")