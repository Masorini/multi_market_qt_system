import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict

from multi_market_qt_system.core.order import Order, OrderType

logger = logging.getLogger(__name__)


class Portfolio:
    def __init__(self, cash: float):
        self.cash = cash
        self.positions: Dict[str, int] = defaultdict(int)  # 当前持仓 symbol -> quantity
        self.trades: list[Order] = []  # 成交订单列表 已执行订单记录
        self.rejected: list[Dict] = []  # 被拒绝的订单及原因
        self.trade_log: list[Dict] = []  # 每次成交后或状态改变时的资产快照
        logger.info("Portfolio initialized with cash: %.2f", cash)

    def get_position(self, symbol: str) -> int:
        return self.positions[symbol]

    def execute_order(self, order: Order, market_prices: Dict[str, float]) -> None:
        """
        执行订单并更新现金、持仓。
        market_prices: 当前市价 dict。
        """
        logger.info("Executing order: %s", order)

        # 1. 计算执行价格：考虑滑点
        base_price = market_prices.get(order.symbol, order.price)
        fill_price = base_price * (1 + order.slippage if order.order_type == OrderType.BUY else 1 - order.slippage)
        # 2. 总成本或收益
        notional = fill_price * order.quantity
        fee = notional * order.commission

        try:
            if order.order_type in (OrderType.BUY, OrderType.COVER):
                total_cost = notional + fee
                if self.cash < total_cost:
                    raise ValueError("Insufficient cash to BUY/COVER")
                self.cash -= total_cost
                self.positions[order.symbol] += order.quantity
                logger.debug("Bought %d of %s at price %.2f, cost %.2f", order.quantity, order.symbol, fill_price, total_cost)
            elif order.order_type in (OrderType.SELL, OrderType.SHORT):
                if self.positions[order.symbol] < order.quantity:
                    raise ValueError("Insufficient position to SELL/SHORT")
                self.cash += notional - fee
                self.positions[order.symbol] -= order.quantity
                logger.debug("Sold %d of %s at price %.2f, proceeds %.2f", order.quantity, order.symbol, fill_price, notional - fee)
            else:
                raise ValueError("Unknown order type")
        except Exception as e:
            logger.warning("Order execution failed: %s, reason: %s", order, e)
            self.rejected.append({
                "order": order,
                "reason": str(e)
            })
            return

        # 成交记录
        self.trades.append(order)
        # 记录快照
        self._log_state(order.timestamp, market_prices)

    def _log_state(self, timestamp: datetime, market_prices: Dict[str, float]):
        # 动态市值计算
        total_pos_value = sum(
            qty * market_prices.get(sym, 0) for sym, qty in self.positions.items()
        )
        snapshot = {
            "timestamp": timestamp,
            "cash": self.cash,
            **{f"pos_{sym}": qty for sym, qty in self.positions.items()},
            "total_value": self.cash + total_pos_value
        }
        self.trade_log.append(snapshot)
        logger.debug("Portfolio snapshot: %s", snapshot)

    def summary(self) -> dict:
        win = sum(1 for o in self.trades if o.order_type == OrderType.SELL and o.price * o.quantity > 0)
        loss = sum(1 for o in self.trades if o.order_type == OrderType.SELL and o.price * o.quantity <= 0)
        result = {
            "final_cash": self.cash,
            "positions": dict(self.positions),
            "total_trades": len(self.trades),
            "rejected_orders": len(self.rejected),
            "winning_trades": win,
            "losing_trades": loss
        }
        logger.info("Portfolio summary: %s", result)
        return result

