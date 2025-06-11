from collections import defaultdict
from datetime import datetime
from multi_market_qt_system.core.order import Order, OrderType

class Portfolio:
    def __init__(self, cash: float):
        self.cash = cash
        self.positions = defaultdict(int)       # symbol -> quantity
        self.trades = []                        # 已执行订单记录
        self.trade_log = []                     # 每次资产快照

    def get_position(self, symbol: str) -> int:
        return self.positions[symbol]

    def execute_order(self, order: Order) -> None:
        total_cost = order.price * order.quantity

        if order.order_type == OrderType.BUY:
            if self.cash < total_cost:
                raise ValueError("余额不足，无法买入")
            self.cash -= total_cost
            self.positions[order.symbol] += order.quantity

        elif order.order_type == OrderType.SELL:
            if self.positions[order.symbol] < order.quantity:
                raise ValueError("持仓不足，无法卖出")
            self.cash += total_cost
            self.positions[order.symbol] -= order.quantity

        self.trades.append(order)
        self._log_state(order.timestamp)

    def _log_state(self, timestamp: datetime):
        snapshot = {
            "timestamp": timestamp,
            "cash": self.cash,
            "positions": dict(self.positions),
            "total_value": self.cash + sum(
                self.get_position(sym) * 1  # 假设价格为1，实际应动态传入当前市价
                for sym in self.positions
            )
        }
        self.trade_log.append(snapshot)

    def summary(self) -> dict:
        return {
            "final_cash": self.cash,
            "final_positions": dict(self.positions),
            "total_trades": len(self.trades)
        }
