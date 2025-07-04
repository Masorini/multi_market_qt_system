from __future__ import annotations
import logging
from typing import Callable, Optional, Union
import pandas as pd
from pydantic import BaseModel, Field, ValidationError
from openbb import obb

logger = logging.getLogger(__name__)


class DataSourceConfig(BaseModel):
    source: str = Field(..., description="数据源名称，如 'openbb' 或 'vnpy'")


class DataClient:
    """
    行情数据接口，支持回测模式的历史数据加载和实盘模式的实时订阅。
    """

    def __init__(self, mode: str, conf: dict) -> None:
        """
        :param mode: 'backtest' 或 'live'
        :param conf: YAML 配置文件加载后的 dict
        """
        self.mode = mode
        ds_cfg = DataSourceConfig(**conf.get('market_data', {}))
        self.source = ds_cfg.source.lower()
        logger.info("DataClient initialized: mode=%s, source=%s", self.mode, self.source)

    def get_historical(
            self, symbol: str, start: str, end: str, provider: str = 'yfinance'
    ) -> pd.DataFrame:
        """
        获取历史 K 线数据
        :param symbol: 交易标的，如 'AAPL' 或 'BTC-USD'
        :param start: 起始日期，格式 YYYY-MM-DD
        :param end: 结束日期，格式 YYYY-MM-DD
        :param provider: 数据提供方
        :return: pandas.DataFrame，包含至少 ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        """
        logger.info("Loading historical data for %s [%s - %s] via %s", symbol, start, end, self.source)
        if self.source == 'openbb':
            try:
                df = obb.equity.price.historical(symbol, start, end, provider).to_df()
                print("Columns:", df.columns.tolist(), "\n")
                logger.debug("Historical data head for %s:\n%s", symbol, df.head(3))
                return df
            except Exception as e:
                logger.exception("Failed to fetch historical data for %s: %s", symbol, e)
                raise
        else:
            logger.error("Unsupported data source: %s", self.source)
            raise NotImplementedError(f"Data source {self.source} not implemented.")

    def subscribe(
            self, symbol: str, callback: Callable[[dict], None]
    ) -> None:
        """
        在实盘模式下订阅实时行情，回调包含最新 bar 或 tick 数据。
        :param symbol: 标的代码
        :param callback: 接收行情的回调函数，参数为标准化 dict 数据
        """
        if self.mode != 'live':
            logger.error("Attempt to subscribe in non-live mode: %s", self.mode)
            raise RuntimeError("实盘模式才能订阅实时行情，请将 mode 设置为 'live'.")
        logger.info("Subscribing to live data for %s via %s", symbol, self.source)
        # TODO: 调用 SDK 的 WebSocket 或 Gateway 接口
        # 示例 （伪代码）:
        # if self.source == 'vnpy':
        #     gateway = VnpyGateway(...) 
        #     gateway.subscribe(symbol, on_tick=callback)
        raise NotImplementedError("实时订阅功能待实现")
