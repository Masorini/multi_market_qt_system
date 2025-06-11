import yaml
from multi_market_qt_system import DataClient
from multi_market_qt_system import DualMAStrategy
from multi_market_qt_system import RiskManager
from multi_market_qt_system import Backtester

if __name__ == '__main__':
    conf = yaml.safe_load(open('config/config.yaml'))
    data_client = DataClient(conf)
    strategy = DualMAStrategy(conf)
    risk_mgr = RiskManager(conf)
    bt = Backtester(conf, data_client, strategy, risk_mgr)
    result = bt.run('AAPL', '2023-01-01', '2025-06-01')
    print(result)