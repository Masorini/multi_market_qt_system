from abc import ABC, abstractmethod
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


class StrategyBase(ABC):
    """
    策略基类，定义策略生命周期与核心接口。
    """
    def __init__(self, name: str, params: Dict[str, Any]) -> None:
        """
        :param name: 策略名称
        :param params: 策略参数字典
        """
        self.name = name
        self.params = params
        self.position = 0      # 当前持仓数量
        self.signals: list[Dict[str, Any]] = []
        logger.info("初始化策略 %s with params: %s", name, params)

    # @abstractmethod
    def on_bar(self, bar: Dict[str, Any]) -> None:
        """
        每当新的 K 线(bar)到达时触发。
        :param bar: 包含 date/open/high/low/close/volume 等字段的字典
        """
        pass

    def emit_signal(self, signal: Dict[str, Any]) -> None:
        """
        生成交易信号并记录。
        :param signal: {'action': 'BUY'/'SELL', 'symbol': str, 'price': float, 'quantity': int}
        """
        logger.debug("策略 %s 发出信号: %s", self.name, signal)
        self.signals.append(signal)

    def get_signals(self) -> list[Dict[str, Any]]:
        """
        获取自上次获取以来所有累积信号，并清空内部缓存。
        """
        sigs = self.signals.copy()
        self.signals.clear()
        return sigs