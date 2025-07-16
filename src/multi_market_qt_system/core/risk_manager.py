from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Union, List, Callable, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    max_position_pct: float = field(default=0.1, metadata={"desc": "单标的最大持仓比例"})
    max_drawdown: float = field(default=0.2, metadata={"desc": "最大回撤率"})
    max_daily_loss_pct: float = field(default=0.02, metadata={"desc": "单日最大亏损比例"})
    max_daily_trades: int = field(default=20, metadata={"desc": "当日最大交易次数"})


class RiskManager:
    """
    风控模块，基于多项规则检查并过滤交易信号，支持规则链化扩展。
    """

    def __init__(self, limits: RiskLimits):
        self.limits = limits
        self.start_equity: float = 0.0
        self.peak_equity: float = 0.0
        self.current_date: datetime.date = None
        self.custom_rules: List[Callable] = []  # List of (order, portfolio) -> (bool, reason)
        logger.info("RiskManager initialized with limits: %s", limits)

    def register_rule(self, rule_func: Callable[[any, any], Tuple[bool, str]]):
        """注册自定义风控规则: rule(order, portfolio) -> (pass: bool, reason: str)"""
        self.custom_rules.append(rule_func)
        logger.debug("Custom rule registered: %s", rule_func)

    def validate(self, order, market_price: Dict[str, float], portfolio) -> bool:
        logger.debug("Validating order: %s", order)
        today = order.timestamp
        # 当日初始
        if self.current_date != today:
            self.current_date = today
            logger.debug("Date changed, reset daily loss and trades")

        # 1) 持仓上限：按市值比例
        pos = portfolio.get_position(order.symbol)
        pos_value = (pos + order.quantity) * market_price[order.symbol]
        total_value = portfolio.current_value(market_price)
        pct = pos_value / total_value
        limit_pct = self.limits.max_position_pct * 100
        logger.debug("[Risk rule=position_pct] Post-order position pct: %.2f%% (limit %.2f%%)", pct * 100,
                     limit_pct)
        if pct > self.limits.max_position_pct:
            logger.warning("[Risk rule=position_pct] Position pct %.2f%% exceeds limit %.2f%%", pct * 100,
                           self.limits.max_position_pct * 100)
            return False

        # 2) 当前回撤
        drawdown = (portfolio.current_value(market_price) - portfolio.peak_value) / portfolio.peak_value
        if drawdown < -self.limits.max_drawdown:
            logger.warning("[Risk rule=drawdown] Drawdown %.2f%% breach", drawdown * 100)
            return False

        # 3) 单日最大亏损：按比例
        # today_pnl = portfolio.calculate_today_pnl(order, market_price)
        today_pnl = order.pnl(market_price)
        pnl_pct = today_pnl / total_value
        logger.debug("[Risk rule=pnl_pct] Today's P&L: %.2f%% (limit -%.2f%%)", pnl_pct * 100,
                     self.limits.max_daily_loss_pct * 100)
        if pnl_pct < -self.limits.max_daily_loss_pct:
            logger.warning("[Risk rule=pnl_pct] Daily loss %.2f%% exceeds limit", pnl_pct * 100)
            return False

        # 4. 当日交易次数
        trades = portfolio.trades_today_count()
        if self.limits.max_daily_trades is not None and trades > self.limits.max_daily_trades:
            logger.warning("[Risk rule=max_daily_trades] Daily trades limit breached: %d>%d", trades,
                           self.limits.max_daily_trades)
            return False

        # 5. 自定义风控规则
        for rule in self.custom_rules:
            ok, reason = rule(order, portfolio)
            if not ok:
                logger.warning("Custom rule blocked: %s", reason)
                return False

        return True
