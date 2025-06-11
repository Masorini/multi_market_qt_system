import yaml
from multi_market_qt_system import DataClient
from multi_market_qt_system import DualMAStrategy
from multi_market_qt_system import RiskManager
from multi_market_qt_system import ExecutionEngine
from multi_market_qt_system import FutuGateway
from multi_market_qt_system import BinanceGateway

if __name__ == '__main__':
    conf = yaml.safe_load(open('config/config.yaml'))
    data_client = DataClient(conf)
    strategy = DualMAStrategy(conf)
    risk_mgr = RiskManager(conf)
    gateways = []
    if conf['brokers']['futu']['enable']:
        gateways.append(FutuGateway(conf['brokers']['futu']))
    if conf['brokers']['binance']['enable']:
        gateways.append(BinanceGateway(conf['brokers']['binance']))
    engine = ExecutionEngine(gateways)

    def on_bar(bar):
        signal = strategy.on_bar(bar)
        if signal and risk_mgr.check(signal, 0, {}):
            engine.execute(signal)

    data_client.subscribe('AAPL', on_bar)