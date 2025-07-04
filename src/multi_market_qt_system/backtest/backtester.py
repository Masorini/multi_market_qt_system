import logging

from multi_market_qt_system.core.data_client import DataClient
from multi_market_qt_system.core.risk_manager import RiskManager
from multi_market_qt_system.core.strategy_base import StrategyBase
from multi_market_qt_system.core.order import Order, OrderType, OrderStyle
from multi_market_qt_system.core.portfolio import Portfolio
from multi_market_qt_system.core.performance import PerformanceMetrics

logger = logging.getLogger(__name__)


class Backtester:
    """
    回测引擎：集成数据获取、策略执行、风控检查与交易模拟。
    """

    def __init__(
            self,
            data_client: DataClient,
            strategy: StrategyBase,
            risk_manager: RiskManager,
            initial_cash: float = 1_000_000,
            commission: float = 0.0005,
            slippage: float = 0.0002
    ):
        self.data_client = data_client
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage
        logger.info("Backtester initialized: initial_cash=%s, commission=%s, slippage=%s", initial_cash, commission, slippage)

    def run(
            self,
            symbol: str,
            start: str,
            end: str,
            interval: str = '1d',
            provider: str = 'yfinance'
    ) -> PerformanceMetrics:
        """
        :param symbol: 标的代码
        :param start: 回测开始日期 YYYY-MM-DD
        :param end: 回测结束日期 YYYY-MM-DD
        :param provider: 数据提供方
        :return: Portfolio 对象（包含现金、持仓、交易记录等）
        """
        logger.info("Backtest run started for %s [%s - %s]", symbol, start, end)

        # 1. 获取历史数据并标准化
        df = self.data_client.get_historical(symbol, start, end, provider)
        df = (
            df.rename(columns=lambda col: col.lower())  # 或者 .columns = [c.lower() for c in df.columns]
            .reset_index()
            .rename(columns={'date': 'timestamp'})
            .set_index('timestamp', drop=False)
            .sort_index()
        )
        logger.debug("DataFrame tail:\n%s", df.tail(3))
        print(df.tail(3), "\n")

        # 2. 初始化资产组合
        portfolio = Portfolio(cash=self.initial_cash)

        # 2.1 记录初始快照：用首日开盘价或收盘价估算市值 (防止"计算绩效指标"结果为 NAN%)
        first_price = df.iloc[0].close
        portfolio._log_state(df.index[0], {symbol: first_price})
        logger.debug("Initial portfolio state logged with price %s", first_price)

        # 3. 回测主循环
        for row in df.itertuples():  # 比 for idx, row in df.iterrows() 性能更快
            bar = {
                'timestamp': row.timestamp,
                'open': row.open,
                'high': row.high,
                'low': row.low,
                'close': row.close,
                'volume': row.volume,
                'symbol': symbol
            }
            logger.debug("Processing bar for %s at %s: close=%.2f", symbol, row.timestamp, row.close)
            # 3.1 生成信号
            signals = self.strategy.on_bar(bar)

            # 3.2 依次处理信号：风控 + 执行
            for sig in signals:
                logger.info("Processing signal: %s", sig)
                # 临时打印 signal 的类型和内容
                print(">> signal:", sig)

                # 构造 Order
                order = Order(
                    timestamp=sig['timestamp'],
                    symbol=sig['symbol'],
                    quantity=sig['quantity'],
                    price=sig['price'],
                    order_type=OrderType.BUY if sig['action'] == 'BUY' else OrderType.SELL,
                    style=OrderStyle.MARKET,
                    commission=self.commission,
                    slippage=self.slippage
                )

                # 当前市价
                market_price = {symbol: row.close}

                # 风控校验
                if not self.risk_manager.validate(order, market_price, portfolio):
                    logger.info("Order blocked by risk manager: %s", order)
                    continue

                # 执行订单
                portfolio.execute_order(order, market_prices=market_price)
                logger.debug("Order executed: %s", order)

        # 4. 计算绩效指标
        perf = PerformanceMetrics.from_portfolio(
            portfolio,
            price_index=df.index
        )
        stats = portfolio.summary()
        logger.info("Backtest completed for %s: stats=%s", symbol, stats)
        print("\nstats: ", stats)
        return perf
