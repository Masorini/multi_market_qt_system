from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class Signal:
    timestamp: datetime
    symbol: str
    action: Literal['BUY','SELL','SHORT','COVER']
    price: float
    quantity: int
