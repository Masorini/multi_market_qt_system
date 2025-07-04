from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Union, List, Callable, Tuple
import logging
from multi_market_qt_system.core.order import OrderType

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    max_position: int = field(default=100, metadata={"desc": "单标的最大持仓量"})
    max_drawdown: float = field(default=0.2, metadata={"desc": "最大回撤率"})
    max_daily_loss: float = field(default=None, metadata={"desc": "当日最大亏损"})
    max_daily_trades: int = field(default=None, metadata={"desc": "当日最大交易次数"})


class RiskManager:
    """
    风控模块，基于多项规则检查并过滤交易信号，支持规则链化扩展。
    """

    def __init__(self, limits: RiskLimits):
        self.limits = limits
        self.start_equity: float = 0.0
        self.peak_equity: float = 0.0
        self.current_date: datetime.date = None
        self.daily_loss: float = 0.0
        self.daily_trades: int = 0
        self.custom_rules: List[Callable] = []  # List of (order, portfolio) -> (bool, reason)

        logger.info("RiskManager initialized with limits: %s", limits)

    def register_rule(self, rule_func: Callable[[any, any], Tuple[bool, str]]):
        """注册自定义风控规则: rule(order, portfolio) -> (pass: bool, reason: str)"""
        self.custom_rules.append(rule_func)
        logger.debug("Custom rule registered: %s", rule_func)

    def validate(self, order, market_price: Dict[str, float], portfolio) -> bool:
        logger.debug("Validating order: %s", order)
        now = order.timestamp
        # 当日初始
        if self.current_date != now:
            self.current_date = now
            self.daily_loss = 0.0
            self.daily_trades = 0
            logger.debug("Date changed, reset daily loss and trades")

        # 1. 持仓量限制
        pos = portfolio.get_position(order.symbol)
        if order.order_type == OrderType.BUY and pos + order.quantity > self.limits.max_position:
            logger.warning("Position limit breached for %s: %d+%d>%d", order.symbol, pos, order.quantity, self.limits.max_position)
            return False

        # 2. 预计成交后净值及回撤
        projected_equity = portfolio.cash
        for sym, qty in portfolio.positions.items():
            # price = order.price if sym == order.symbol else portfolio.positions[sym]
            price = market_price.get(sym, 0.0)
            projected_equity += qty * price
        self.peak_equity = max(self.peak_equity, projected_equity)
        drawdown = (self.peak_equity - projected_equity) / self.peak_equity
        if drawdown > self.limits.max_drawdown:
            logger.warning("Drawdown limit breached: %.2%>%.2%", drawdown, self.limits.max_drawdown)
            return False

        # 3. 当日累计亏损
        pnl = (-order.price * order.quantity) if order.order_type in (OrderType.BUY,) else (
                    order.price * order.quantity)
        self.daily_loss += pnl
        if self.limits.max_daily_loss is not None and abs(self.daily_loss) > self.limits.max_daily_loss:
            logger.warning("Daily loss limit breached: %s>%s", abs(self.daily_loss), self.limits.max_daily_loss)
            return False

        # 4. 当日交易次数
        self.daily_trades += 1
        if self.limits.max_daily_trades is not None and self.daily_trades > self.limits.max_daily_trades:
            logger.warning("Daily trades limit breached: %d>%d", self.daily_trades, self.limits.max_daily_trades)
            return False

        # 5. 自定义风控规则
        for rule in self.custom_rules:
            ok, reason = rule(order, portfolio)
            if not ok:
                logger.warning("Custom rule blocked: %s", reason)
                return False

        return True
