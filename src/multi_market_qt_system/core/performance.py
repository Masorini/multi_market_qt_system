from __future__ import annotations

import logging
from dataclasses import dataclass
import pandas as pd
import numpy as np
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """
    回测绩效指标，包括：
    - equity_curve: 资金曲线 (时间索引的 pandas.Series)
    - period_returns: 每期收益 (百分比)
    - cumulative_returns: 累计收益曲线
    - total_return: 总收益率
    - annual_return: 年化收益率
    - annual_volatility: 年化波动率
    - sharpe_ratio: 年化 Sharpe 比率 (无风险利率默认为0)
    - max_drawdown: 最大回撤
    - sortino_ratio: 年化 Sortino 比率
    - calmar_ratio: Calmar 比率
    """
    equity_curve: pd.Series
    period_returns: pd.Series
    cumulative_returns: pd.Series
    total_return: float
    annual_return: float
    annual_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    sortino_ratio: float
    calmar_ratio: float

    @classmethod
    def from_portfolio(
            cls,
            portfolio,
            price_index: Optional[pd.DatetimeIndex] = None,
            trading_days: int = 252,
            risk_free_rate: float = 0.0
    ) -> PerformanceMetrics:
        logger.info("Calculating performance metrics...")
        # 1. 构造净值序列
        df = (
            pd.DataFrame(portfolio.trade_log)
            .assign(timestamp=lambda d: pd.to_datetime(d['timestamp']))
            .set_index('timestamp')
        )
        equity = df['total_value'].sort_index()
        logger.debug("Equity series head:% s", equity.head())

        # —— 插入回测/首日初始净值点 —— #
        if price_index is not None:
            # 使用 price_index 的第一个元素，但强转为 pd.Timestamp
            start = pd.to_datetime(price_index[0])
        else:
            start = equity.index[0]

        # 如果首日还没记录快照，就手动 prepend
        if start not in equity.index or pd.isna(equity.iloc[0]):
            # 初始净值我们取 portfolio.cash（假设建仓前无持仓市值）
            init_val = portfolio.cash
            pre = pd.Series([init_val], index=[start])
            equity = pd.concat([pre, equity]).sort_index()
            logger.debug("Prepended initial equity: %s at %s", init_val, start)

        # 2. 如有完整行情索引，则前向填充，保证日期连续
        if price_index is not None:
            equity = equity.reindex(price_index).ffill()
            logger.debug("Equity after reindex/ffill head: %s", equity.head())

        # 3. 计算周期收益（剔除 NaN）
        period_returns = equity.pct_change(fill_method=None).dropna()

        # 4. 累计收益曲线
        cumulative_returns = (1 + period_returns).cumprod() - 1

        # 5. 总收益率
        total_return = equity.iloc[-1] / equity.iloc[0] - 1

        # 6. 年化收益率（基于日历天数折算）
        days = max((equity.index[-1] - equity.index[0]).days, 1)
        annual_return = (1 + total_return) ** (365.0 / days) - 1

        # 7. 年化波动率
        annual_volatility = period_returns.std() * np.sqrt(trading_days)

        # 8. Sharpe 比率
        sharpe_ratio = ((annual_return - risk_free_rate) / annual_volatility
                        if annual_volatility else np.nan)

        # 9. 最大回撤
        rolling_max = equity.cummax()
        drawdown = (equity - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # 10. Sortino 比率（只计算下行波动率）
        downside_returns = period_returns.copy()
        downside_returns[downside_returns > 0] = 0
        downside_vol = downside_returns.std() * np.sqrt(trading_days)
        sortino_ratio = ((annual_return - risk_free_rate) / downside_vol
                         if downside_vol else np.nan)

        # 11. Calmar 比率（年化收益 / 最大回撤）
        calmar_ratio = (annual_return / abs(max_drawdown)
                        if max_drawdown != 0 else np.nan)

        logger.info(
            "Metrics calculated: total_return=%.2f%% annual_return=%.2f%% sharpe=%.2f max_drawdown=%.2f%%",
            total_return * 100,
            annual_return * 100,
            sharpe_ratio,
            max_drawdown * 100
        )

        return cls(
            equity_curve=equity,
            period_returns=period_returns,
            cumulative_returns=cumulative_returns,
            total_return=total_return,
            annual_return=annual_return,
            annual_volatility=annual_volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio
        )
