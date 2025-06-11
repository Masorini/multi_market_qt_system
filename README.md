multi_market_qt_system/           # 根目录
├── config/                     # 配置文件目录
│   └── config.yaml             # 全局配置（API keys、交易所、策略参数）
├── core/                       # 核心模块
│   ├── data_client.py          # 行情数据接口
│   ├── strategy_base.py        # 策略基类与公共工具
│   ├── risk_manager.py         # 风控模块
│   └── utils.py                # 通用工具函数
├── strategies/                 # 策略实现
│   └── dual_ma_strategy.py     # 示例：双均线策略
├── backtest/                   # 回测模块
│   └── backtester.py           # 回测引擎
├── broker/                     # 实盘交易网关
│   ├── futu_gateway.py         # 富途 OpenAPI 网关
│   └── binance_gateway.py      # 币安 REST/WebSocket 网关
├── execution/                  # 执行引擎
│   └── execution_engine.py     # 实盘下单执行模块
├── logs/                       # 日志文件目录
├── scripts/                    # 启动脚本
│   ├── run_backtest.py         # 回测入口脚本
│   └── run_live.py             # 实盘运行脚本
├── requirements.txt            # Python 依赖列表
├── README.md                   # 项目说明文档
└── .gitignore                  # Git 忽略配置


multi_market_qt_system/
├── pyproject.toml           # 或者 setup.py + setup.cfg
├── src/
│   └── multi_market_qt_system/
│       ├── __init__.py
│       ├── main.py          # CLI 入口
│       ├── config.py        # 配置加载
│       ├── core/            # 之前的 core 模块
│       ├── strategies/
│       ├── backtest/
│       ├── broker/
│       └── execution/
├── tests/                   # 单元测试
├── README.md
└── .gitignore