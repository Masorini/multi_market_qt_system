import logging
from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime

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
