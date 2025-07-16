class PositionSizer:
    """
    根据可用现金 & 信号强度计算订单数量。
    """

    def __init__(self, trade_pct: float = 0.05):
        """
        :param trade_pct: 本次下单占用现金的比例，默认 5%
        """
        self.trade_pct = trade_pct

    def size(self, cash: float, price: float) -> int:
        # 分配的资金
        alloc = cash * self.trade_pct
        # 向下取整为整数手数
        return max(int(alloc // price), 1)
