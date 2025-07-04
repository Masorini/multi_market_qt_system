import logging
import os
import click
import yaml
from multi_market_qt_system.core.performance import PerformanceMetrics
from multi_market_qt_system.logs.logging_config import init_logging
from multi_market_qt_system.visualization.plotting import create_performance_dashboard
from .core.data_client import DataClient
from .strategies.dual_ma_strategy import DualMAStrategy, DualMAStrategyConfig
from .core.risk_manager import RiskManager, RiskLimits
from .backtest.backtester import Backtester
from pathlib import Path

logger = logging.getLogger(__name__)

# 默认配置路径
DEFAULT_CONFIG = Path(__file__).resolve().parent / 'config' / 'config.yaml'


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    '--config', '-c',
    type=click.Path(exists=True, dir_okay=False),
    default=str(DEFAULT_CONFIG),
    help="YAML 配置文件路径"
)
@click.pass_context
def cli(ctx, config):
    """
    多市场量化交易系统 CLI。
    使用 --config 指定不同环境的配置文件。
    """
    # 1) 加载配置
    with open(config, 'r') as f:
        conf = yaml.safe_load(f)
    # 2) 环境变量覆盖
    conf['mode'] = os.getenv('MODE', conf.get('mode', 'backtest'))
    logger.debug("Configuration loaded: %s", conf)
    ctx.obj = conf

    # —— 从配置中初始化日志 —— #
    log_cfg = conf.get('logging', {})
    level_name = log_cfg.get('level', 'INFO').upper()
    level = getattr(logging, level_name, logging.INFO)
    init_logging(
        console=log_cfg.get('console', False),
        level=level
    )
    logger.info("Logging initialized, level=%s, dir=%s, file=%s, console=%s", level_name,
                log_cfg.get('log_dir'), log_cfg.get('log_file'), log_cfg.get('console'))


@cli.command()
@click.option('--symbol', '-s', default='AAPL', help="回测标的，支持多个逗号分隔")
@click.option('--start', default='2023-01-01', help="回测开始日期 YYYY-MM-DD")
@click.option('--end', default='2025-06-01', help="回测结束日期 YYYY-MM-DD")
@click.option('--provider', default='yfinance', help="数据提供方，覆盖 config.market_data.source")
@click.pass_context
def backtest(ctx, symbol, start, end, provider):
    """
    运行回测，输出绩效指标。
    """
    conf = ctx.obj
    symbols = [s.strip() for s in symbol.split(',')]
    logger.info("Begin backtest for symbols: %s from %s to %s with provider %s", symbols, start, end, provider)

    # 1. 数据客户端
    data_client = DataClient(conf['mode'], conf)
    logger.debug("DataClient initialized: mode=%s, source=%s", conf['mode'], conf.get('market_data', {}))

    # 2. 策略实例化
    strat_cfg = DualMAStrategyConfig(**conf['strategy']['params'])
    strat_name = conf['strategy']['name']
    strategy = DualMAStrategy(name=strat_name, config=strat_cfg)
    logger.debug("Strategy %s initialized with config %s", strat_name, strat_cfg)

    # 3. 风控管理器
    rc_conf = conf.get('risk_control', {})
    limits = RiskLimits(
        max_position=rc_conf.get('max_position', 100),
        max_drawdown=rc_conf.get('max_drawdown', 0.2),
        max_daily_loss=rc_conf.get('max_daily_loss'),
        max_daily_trades=rc_conf.get('max_daily_trades')
    )
    risk_mgr = RiskManager(limits)
    logger.debug("RiskManager initialized with limits: %s", limits)

    # 4. 回测引擎
    bt = Backtester(
        data_client=data_client,
        strategy=strategy,
        risk_manager=risk_mgr,
        initial_cash=conf.get('initial_cash', 1_000_000),
        commission=conf.get('commission', 0.0005),
        slippage=conf.get('slippage', 0.0002)
    )
    logger.info("Backtester created: initial_cash=%s, commission=%s, slippage=%s", conf.get('initial_cash'),
                conf.get('commission'), conf.get('slippage'))

    # 5. 执行回测
    for sym in symbols:
        logger.info("Running backtest for %s", sym)
        try:
            perf: PerformanceMetrics = bt.run(
                symbol=sym,
                start=start,
                end=end,
                provider=provider or conf['market_data']['source']
            )
            logger.info("Backtest completed for %s: total_return=%.2f%%", sym, perf.total_return * 100)
        except Exception as e:
            logger.exception("Backtest failed for %s: %s", sym, e)
            continue

        # 6. 打印结果
        click.echo(f"\n=== Backtest Results for {sym}: {start} → {end} ===")
        click.echo(f"Total Return:      {perf.total_return:.2%}")
        click.echo(f"Annual Return:     {perf.annual_return:.2%}")
        click.echo(f"Annual Volatility: {perf.annual_volatility:.2%}")
        click.echo(f"Sharpe Ratio:      {perf.sharpe_ratio:.2f}")
        click.echo(f"Max Drawdown:      {perf.max_drawdown:.2%}")
        click.echo(f"Sortino Ratio:     {perf.sortino_ratio:.2f}")
        click.echo(f"Calmar Ratio:      {perf.calmar_ratio:.2f}")

        # 7.可视化
        fig = create_performance_dashboard(
            perf.equity_curve,
            perf.period_returns,
            output_path='src/multi_market_qt_system/visualization/reports/perf_dashboard.html'
        )
        # fig.show()


@cli.command()
@click.pass_context
def live(ctx):
    """
    实盘交易（待实现）。
    """
    logger.warning("Live trading mode invoked but not implemented.")
    click.echo("Live trading mode is not yet implemented.")


if __name__ == '__main__':
    cli()
