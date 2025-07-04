import calendar
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_performance_dashboard(
    equity: pd.Series,
    returns: pd.Series,
    output_path: str = None
) -> go.Figure:
    """
    生成 2x2 子图的大型 Performance Dashboard。可选保存到 HTML。

    :param equity: 时间序列净值
    :param returns: 时间序列收益率
    :param output_path: 如果指定，则保存 HTML
    :return: Plotly Figure
    """
    # 计算回撤
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max

    # 确保 equity.index 为 DatetimeIndex
    equity.index = pd.to_datetime(equity.index)

    # 计算月度收益热力图数据
    monthly = equity.resample('ME').last().pct_change().dropna()
    heat_df = monthly.to_frame('monthly_return')
    heat_df['year'] = heat_df.index.year
    heat_df['month'] = heat_df.index.month
    pivot = heat_df.pivot(index='year', columns='month', values='monthly_return')

    # 创建 2x2 子图
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            'Equity Curve', 'Drawdown',
            'Return Distribution', 'Monthly Heatmap'
        ],
        horizontal_spacing=0.1,
        vertical_spacing=0.12
    )

    # 子图① 净值曲线
    fig.add_trace(
        go.Scatter(
            x=equity.index, y=equity.values,
            mode='lines', name='Equity'
        ), row=1, col=1
    )

    # 子图② 回撤
    fig.add_trace(
        go.Scatter(
            x=drawdown.index, y=drawdown.values,
            mode='lines', name='Drawdown', line=dict(color='firebrick')
        ), row=1, col=2
    )

    # 子图③ 收益分布
    hist_vals, hist_bins = np.histogram(returns, bins=50)
    fig.add_trace(
        go.Bar(
            x=hist_bins[:-1], y=hist_vals,
            name='Return Dist'
        ), row=2, col=1
    )

    # 子图④ 月度热力图
    fig.add_trace(
        go.Heatmap(
            z=pivot.values,
            x=[calendar.month_abbr[m] for m in pivot.columns],
            y=pivot.index.astype(str),
            colorscale='RdYlGn',
            colorbar=dict(title='Return')
        ), row=2, col=2
    )

    # 布局调整
    fig.update_layout(
        height=900,
        width=1400,
        title_text='Performance Dashboard',
        template='plotly_white'
    )

    # 保存
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(out))
        print(f"仪表盘已保存: {out}")

    return fig