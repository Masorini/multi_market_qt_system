import logging
from collections import defaultdict
from datetime import datetime, date
from typing import Dict, Optional

from multi_market_qt_system.core.order import Order, OrderType

logger = logging.getLogger(__name__)


class Portfolio:
    def __init__(self, cash: float):
        self.cash = cash
        self.positions: Dict[str, int] = defaultdict(int)  # 当前持仓 symbol -> quantity
        self.trades: list[Order] = []  # 成交订单列表 已执行订单记录
        self.rejected: list[Dict] = []  # 被拒绝的订单及原因
        self.trade_log: list[Dict] = []  # 每次成交后或状态改变时的资产快照
        # 新增一个属性跟踪当日 P&L 和交易计数
        self._today_date: Optional[date] = None
        self._today_pnl: float = 0.0
        self._today_trades: int = 0
        # track peak equity
        self.peak_value: float = cash
        self.total_signals: int = 0
        logger.info("Portfolio initialized with cash: %.2f", cash)

    def get_position(self, symbol: str) -> int:
        return self.positions[symbol]

    def execute_order(self, order: Order, market_prices: Dict[str, float]) -> None:
        """
        执行订单并更新现金、持仓；在成功执行前后更新今日 PnL、交易次数和 peak_value。
        :param order: Order 对象
        :param market_prices: dict, {symbol: price}
        """
        logger.info("Executing order: %s", order)

        today = order.timestamp
        # 日切：如果进入新的一天，重置 _today_pnl 和 _today_trades
        if self._today_date != today:
            self._today_date = today
            self._today_pnl = 0.0
            self._today_trades = 0

        # 1) 先计算本笔订单的盈亏（包括手续费和滑点）
        pnl = order.pnl(market_prices)
        # 2) 校验现金/持仓是否足够
        fill_price = order.fill_price(market_prices)
        notional = order.notional(market_prices)
        fee = order.fee(market_prices)
        try:
            if order.order_type in (OrderType.BUY, OrderType.COVER):
                total_cost = notional + fee
                if self.cash < total_cost:
                    raise ValueError("Insufficient cash to BUY/COVER")
                self.cash -= total_cost
                self.positions[order.symbol] += order.quantity
                logger.debug("Bought %d of %s at price %.2f, cost %.2f", order.quantity, order.symbol, fill_price,
                             total_cost)
            elif order.order_type in (OrderType.SELL, OrderType.SHORT):
                if self.positions[order.symbol] < order.quantity:
                    raise ValueError("Insufficient position to SELL/SHORT")
                self.cash += notional - fee
                self.positions[order.symbol] -= order.quantity
                logger.debug("Sold %d of %s at price %.2f, proceeds %.2f", order.quantity, order.symbol, fill_price,
                             notional - fee)
            else:
                raise ValueError("Unknown order type")
        except Exception as e:
            logger.warning("Order execution failed: %s, reason: %s", order, e)
            self.rejected.append({"order": order, "reason": str(e)})
            return

        # 3) 成交记录与日内统计
        self.trades.append(order)
        self._today_pnl += pnl
        self._today_trades += 1

        # 4) 快照并更新 peak_value
        self._log_state(order.timestamp, market_prices)
        current_val = self.current_value(market_prices)
        if current_val > self.peak_value:
            self.peak_value = current_val

        logger.debug(
            "Executed %s %d of %s @%.2f | PnL=%.2f | today PnL=%.2f | peak equity=%.2f",
            order.order_type.name, order.quantity, order.symbol,
            fill_price, pnl, self._today_pnl, self.peak_value
        )

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
            "total_signals": self.total_signals,
            "total_trades": len(self.trades),
            "rejected_orders": len(self.rejected),
            "winning_trades": win,
            "losing_trades": loss
        }
        logger.info("Portfolio summary: %s", result)
        return result

    def current_value(self, market_prices: Dict[str, float]) -> float:
        """返回当前市值：现金 + 持仓市值之和"""
        pos_value = sum(qty * market_prices.get(sym, 0.0) for sym, qty in self.positions.items())
        return self.cash + pos_value

    def trades_today_count(self) -> int:
        """返回当天已执行（非拒单）的成交次数"""
        return self._today_trades
