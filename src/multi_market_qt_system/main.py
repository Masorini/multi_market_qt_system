import click
import yaml
from .core.data_client import DataClient
from .strategies.dual_ma_strategy import DualMAStrategy, DualMAStrategyConfig
from .core.risk_manager import RiskManager
from .backtest.backtester import Backtester
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent  # 脚本上1级到项目根目录
config_path = BASE_DIR / 'config' / 'config.yaml'

with open(config_path, 'r') as f:
    conf = yaml.safe_load(f)


@click.group()
def cli():
    """多市场量化交易系统 CLI 工具"""
    pass


@cli.command()
@click.option('--symbol', default='AAPL')
@click.option('--start', default='2023-01-01')
@click.option('--end', default='2025-06-01')
def backtest(symbol, start, end):
    """运行回测"""
    # conf = yaml.safe_load(open('config/config.yaml'))
    data_client = DataClient('backtest', conf)

    # 构建策略
    strat_conf_dict = conf['strategy']['params']
    strategy_config = DualMAStrategyConfig(**strat_conf_dict)
    strategy_params = strat_conf_dict.copy()  # 也可包含 name、trade_size 等
    strategy_name = conf['strategy']['name']
    strategy = DualMAStrategy(
        name=strategy_name,
        params=strategy_params,
        config=strategy_config
    )

    # 风控管理器
    rc_conf = conf.get('risk_control', {})
    risk_mgr = RiskManager(
        max_position=rc_conf.get('max_position', 100),
        max_drawdown=rc_conf.get('max_drawdown', 0.2)
    )

    # 回测引擎
    bt = Backtester(
        data_client=data_client,
        strategy=strategy,
        risk_manager=risk_mgr,
        initial_cash=conf.get('initial_cash', 1_000_000)
    )

    # 获取历史数据 & 运行
    portfolio = bt.run(symbol, start, end)
    print(portfolio.summary())


if __name__ == '__main__':
    cli()
