from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime

class OrderType(Enum):
    BUY = auto()
    SELL = auto()

@dataclass
class Order:
    timestamp: datetime
    symbol: str
    quantity: int
    price: float
    order_type: OrderType

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("订单数量必须为正整数")
        if self.price <= 0:
            raise ValueError("订单价格必须为正数")
