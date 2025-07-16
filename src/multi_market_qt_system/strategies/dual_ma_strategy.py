import logging
import os
from collections import deque
from dataclasses import dataclass
from typing import Dict, Any, List

import pandas as pd

from multi_market_qt_system.core.strategy_base import StrategyBase

logger = logging.getLogger(__name__)


@dataclass
class DualMAStrategyConfig:
    short_window: int = 20
    long_window: int = 50
    trade_pct: float = 0.05


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
        # ma_history 元素格式：{"timestamp": datetime, "short_ma": float, "long_ma": float}
        self.ma_history: List[Dict[str, Any]] = []
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
            oldest_short = None
            self.short_sum += price

        # 入队
        self.prices.append(price)

        # 不足以计算长均线时，直接返回
        if len(self.prices) < self.config.long_window:
            self.ma_history.append({"timestamp": ts, "short_ma": float("nan"), "long_ma": float("nan")})
            return

        # 计算最新与前一周期的均线
        short_ma = self.short_sum / self.config.short_window
        long_ma = self.long_sum / self.config.long_window

        # 计算前一周期的和，用于上期均线
        prev_long_sum = (self.long_sum - price + (oldest_long or 0))
        prev_short_sum = (self.short_sum - price + (oldest_short or 0))

        prev_short_ma = prev_short_sum / self.config.short_window
        prev_long_ma = prev_long_sum / self.config.long_window
        logger.debug(
            "MA values %s: prev_short=%.2f, prev_long=%.2f, short=%.2f, long=%.2f",
            sym, prev_short_ma, prev_long_ma, short_ma, long_ma
        )

        # 记录均线值
        self.ma_history.append({"timestamp": ts, "short_ma": short_ma, "long_ma": long_ma})

        # 金叉开多
        if prev_short_ma <= prev_long_ma and short_ma > long_ma:
            logger.info("Golden cross BUY signal for %s at %.2f", sym, price)
            self.emit_signal(ts, sym, 'BUY', price)

        # 死叉平多
        elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
            logger.info("Death cross SELL signal for %s at %.2f", sym, price)
            self.emit_signal(ts, sym, 'SELL', price)

    def get_ma_df(self) -> pd.DataFrame:
        """
        将内存里的 MA 记录转成 DataFrame，index 为 timestamp。
        """
        df = pd.DataFrame(self.ma_history)
        return df.set_index("timestamp", drop=False)

    def save_ma_history(self, symbol: str, start: str, end: str, folder: str):
        """
        把 MA 历史保存到 CSV，并在日志里记录路径。
        """
        os.makedirs(folder, exist_ok=True)
        df = self.get_ma_df()
        filename = f"ma_{symbol}_{start}_{end}.csv"
        path = os.path.join(folder, filename)
        df.to_csv(path, index=True)
        logger.info("Saved MA history to %s", path)
        return path

    def log_ma_history(self, head_n: int = 5, tail_n: int = 5):
        """
        把 MA 历史的前后几行打印到 logger.DEBUG 里，便于快速查看。
        """
        df = self.get_ma_df()
        logger.debug("MA history head:\n%s", df.head(head_n))
        logger.debug("MA history tail:\n%s", df.tail(tail_n))
