from dataclasses import dataclass
from datetime import datetime

@dataclass
class Signal:
    timestamp: datetime
    signal_type: str  # 'buy' or 'sell'
