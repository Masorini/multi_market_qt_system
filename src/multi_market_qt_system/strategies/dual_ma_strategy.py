import logging
from collections import deque
from dataclasses import dataclass
from typing import Dict, Any, List
from multi_market_qt_system.core.strategy_base import StrategyBase

logger = logging.getLogger(__name__)


@dataclass
class DualMAStrategyConfig:
    short_window: int = 20
    long_window: int = 50
    trade_size: int = 1  # 每次交易手数


class DualMAStrategy(StrategyBase):
    """
    双均线策略：金叉开多，死叉平多。使用增量算法，O(1) 更新均线。
    """

    def __init__(self,
                 name: str,
                 config: DualMAStrategyConfig):
        super().__init__(name)
        assert config.short_window < config.long_window, "short_window must be < long_window"
        self.config = config
        # 存储最近 N 根收盘价
        self.prices = deque(maxlen=self.config.long_window)
        # 分别维护短均线和长均线的滑动和
        self.short_sum = 0.0
        self.long_sum = 0.0
        logger.info("Initialized DualMAStrategy %s with config %s", name, config)

    def generate(self, bar: Dict[str, Any]) -> None:
        price = bar['close']
        ts = bar['timestamp']
        sym = bar['symbol']
        logger.debug("Received bar: %s %s @ %.2f", sym, ts, price)

        # 更新长均线和
        if len(self.prices) == self.config.long_window:
            # 最早的 price
            oldest_long = self.prices[0]
            self.long_sum += price - oldest_long
        else:
            oldest_long = None
            self.long_sum += price

        # 更新短均线和
        if len(self.prices) >= self.config.short_window:
            # 短窗口中新淘汰的元素
            # 负索引 从列表末尾往回数 short_window 个元素
            oldest_short = list(self.prices)[-self.config.short_window]
            self.short_sum += price - oldest_short
        else:
            self.short_sum += price

        # 入队
        self.prices.append(price)

        # 不足以计算长均线时，直接返回
        if len(self.prices) < self.config.long_window:
            return

        # 计算最新与前一周期的均线
        short_ma = self.short_sum / self.config.short_window
        long_ma = self.long_sum / self.config.long_window

        # 计算前一周期的和，用于上期均线
        prev_long_sum = (self.long_sum - price + (oldest_long or 0))
        prev_short_sum = (self.short_sum - price + (
            oldest_long if oldest_long is not None and len(self.prices) == self.config.long_window else 0))

        prev_short_ma = prev_short_sum / self.config.short_window
        prev_long_ma = prev_long_sum / self.config.long_window
        logger.debug(
            "MA values %s: prev_short=%.2f, prev_long=%.2f, short=%.2f, long=%.2f",
            sym, prev_short_ma, prev_long_ma, short_ma, long_ma
        )

        # 金叉开多
        if prev_short_ma <= prev_long_ma and short_ma > long_ma:
            logger.info("Golden cross BUY signal for %s at %.2f", sym, price)
            self.emit_signal(ts, sym, 'BUY', price, self.config.trade_size)

        # 死叉平多
        elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
            logger.info("Death cross SELL signal for %s at %.2f", sym, price)
            self.emit_signal(ts, sym, 'SELL', price, self.config.trade_size)
