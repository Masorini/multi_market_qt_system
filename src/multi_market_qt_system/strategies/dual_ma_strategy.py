from dataclasses import dataclass
from typing import Dict, Any

from multi_market_qt_system.core.strategy_base import StrategyBase
import pandas as pd
from multi_market_qt_system.core.signal import Signal


@dataclass
class DualMAStrategyConfig:
    short_window: int = 20
    long_window: int = 50
    trade_size: int = 1  # 每次交易手数

class DualMAStrategy(StrategyBase):
    """
    简单双均线策略：
    - 短期均线上穿长期均线时买入
    - 短期均线下穿长期均线时全部卖出
    """
    def __init__(self, name: str, params: Dict[str, Any], config: DualMAStrategyConfig):
        super().__init__(name, params)
        self.config = config

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        signals = []
        data = data.copy()
        data['short_ma'] = data['close'].rolling(window=self.config.short_window).mean()
        data['long_ma'] = data['close'].rolling(window=self.config.long_window).mean()

        data['signal'] = 0
        data.loc[data['short_ma'] > data['long_ma'], 'signal'] = 1
        data.loc[data['short_ma'] < data['long_ma'], 'signal'] = -1

        data['signal_change'] = data['signal'].diff()
        for index, row in data.iterrows():
            if row['signal_change'] == 2:
                signals.append(Signal(timestamp=row.name, signal_type='buy'))
            elif row['signal_change'] == -2:
                signals.append(Signal(timestamp=row.name, signal_type='sell'))
        return signals