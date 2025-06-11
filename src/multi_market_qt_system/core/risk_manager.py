from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class RiskManager:
    """
    风控模块，基于预设规则检查并过滤交易信号。
    """
    def __init__(self, max_position: int, max_drawdown: float) -> None:
        """
        :param max_position: 最大持仓量
        :param max_drawdown: 最大可承受回撤比例（0-1）
        """
        self.max_position = max_position
        self.max_drawdown = max_drawdown
        logger.info(
            "风控初始化: max_position=%s, max_drawdown=%s",
            max_position, max_drawdown
        )

    def validate(
        self,
        signal: Dict[str, Any],
        current_positions: Dict[str, int],
        account_metrics: Dict[str, Any]
    ) -> bool:
        """
        检查信号是否合法。
        :param signal: 交易信号字典
        :param current_positions: 当前持仓量字典
        :param account_metrics: 账户相关指标（如净值、历史最大回撤）
        :return: True 表示通过风控，否则 False
        """
        symbol = signal['symbol']
        qty = signal['quantity']
        action = signal['action']

        # 持仓上限检查
        pos = current_positions.get(symbol, 0)
        if action == 'BUY' and pos + qty > self.max_position:
            logger.warning(
                "风控阻止买入 %s, 当前持仓 %s, 申请 %s 超过上限 %s",
                symbol, pos, qty, self.max_position
            )
            return False

        # 最大回撤检查
        dd = account_metrics.get('drawdown', 0.0)
        if dd > self.max_drawdown:
            logger.warning(
                "风控阻止交易, 当前回撤 %s 已超过最大回撤 %s",
                dd, self.max_drawdown
            )
            return False

        # TODO: 添加更多风控规则（单日最大交易次数、订单价格偏离度等）
        return True