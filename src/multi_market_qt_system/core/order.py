import logging
from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)


class OrderType(Enum):
    BUY = auto()
    SELL = auto()
    SHORT = auto()
    COVER = auto()


class OrderStyle(Enum):
    MARKET = auto()
    LIMIT = auto()
    STOP = auto()


@dataclass
class Order:
    timestamp: datetime
    symbol: str
    quantity: int
    price: float
    order_type: OrderType
    style: OrderStyle = OrderStyle.MARKET
    commission: float = 0.0  # fee rate, e.g., 0.0005
    slippage: float = 0.0  # slippage rate, e.g., 0.0002

    def __post_init__(self):
        logger.debug("Initializing Order: %s %s %d @ %.2f", self.timestamp, self.symbol, self.quantity, self.price)
        if self.quantity <= 0:
            logger.error("Order quantity must be positive: %d", self.quantity)
            raise ValueError("订单数量必须为正整数")
        if self.price <= 0:
            logger.error("Order price must be positive: %.2f", self.price)
            raise ValueError("订单价格必须为正数")
        logger.info("Order created: %s", self)

    def fill_price(self, market_prices: Dict[str, float]) -> float:
        """根据买卖方向和滑点，计算最终成交价"""
        if self.order_type in (OrderType.BUY,):
            return market_prices.get(self.symbol, self.price) * (1 + self.slippage)
        else:
            return market_prices.get(self.symbol, self.price) * (1 - self.slippage)

    def notional(self, market_prices: Dict[str, float]) -> float:
        """成交额 = fill_price * quantity"""
        return self.fill_price(market_prices) * self.quantity

    def fee(self, market_prices: Dict[str, float]) -> float:
        """手续费 = notional * commission"""
        return self.notional(market_prices) * self.commission

    def pnl(self, market_prices: Dict[str, float]) -> float:
        """
        这笔成交对现金流的影响：卖出为正、买入为负，已扣手续费。
        “PnL” 是 “Profit and Loss” 的缩写，直译为“盈亏”
        """
        n = self.notional(market_prices)
        f = self.fee(market_prices)
        if self.order_type in (OrderType.SELL, OrderType.COVER):
            return n - f
        elif self.order_type in (OrderType.BUY, OrderType.SHORT):
            return - (n + f)
        else:
            return 0.0
