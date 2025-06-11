# setup.py
from setuptools import setup, find_packages

setup(
    name="multi_market_qt_system",
    version="0.1.0",
    description="Multi‐market quantitative trading system",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "PyYAML",
        "pydantic",
        "pandas",
        "openbb",
        "futu-api",
        "python-binance",
        "click"
    ],
    entry_points={
        "console_scripts": [
            "mmqt=multi_market_qt_system.main:cli",
        ],
    },
)
