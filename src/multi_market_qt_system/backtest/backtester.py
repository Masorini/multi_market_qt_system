from multi_market_qt_system.core.data_client import DataClient
from multi_market_qt_system.core.risk_manager import RiskManager
from multi_market_qt_system.core.strategy_base import StrategyBase
from multi_market_qt_system.core.order import Order, OrderType
from multi_market_qt_system.core.portfolio import Portfolio
import pandas as pd


class Backtester:
    """
    回测引擎：集成数据获取、策略执行、风控检查与交易模拟。
    """
    def __init__(
        self,
        data_client: DataClient,
        strategy: StrategyBase,
        risk_manager: RiskManager,
        initial_cash: float = 1_000_000
    ) -> None:
        self.data_client = data_client
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.initial_cash = initial_cash

    def run(
        self,
        symbol: str,
        start: str,
        end: str,
        provider: str = 'yfinance'
    ) -> Portfolio:
        """
        :param symbol: 标的代码
        :param start: 回测开始日期 YYYY-MM-DD
        :param end: 回测结束日期 YYYY-MM-DD
        :param provider: 数据提供方
        :return: Portfolio 对象（包含现金、持仓、交易记录等）
        """
        # 1. 获取历史数据
        df = self.data_client.get_historical(symbol, start, end, provider)

        # 2. 初始化组合
        portfolio = Portfolio(cash=self.initial_cash)

        # 3. 遍历 K 线并执行策略 / 风控 / 下单
        for row in df.itertuples():
            bar = {
                'timestamp': row.date,
                'open': row.open,
                'high': row.high,
                'low': row.low,
                'close': row.close,
                'volume': row.volume,
                'symbol': symbol
            }
            # 策略生成信号
            signals = self.strategy.generate_signals(pd.DataFrame([bar]))

            # 风控过滤并执行
            for sig in signals:
                if self.risk_manager.validate(sig, portfolio.positions, {'drawdown': 0.0}):
                    order = Order(
                        timestamp=sig.timestamp,
                        symbol=sig.symbol,
                        quantity=sig.quantity,
                        price=sig.price,
                        order_type=OrderType.BUY if sig.signal_type == 'buy' else OrderType.SELL
                    )
                    portfolio.execute_order(order)

        return portfolio
