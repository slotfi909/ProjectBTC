# ProjectBTC

Python experiments for candlestick-based cryptocurrency trading on BingX and historical BTC/USDT strategy checks. The exchange runner is in `bingx/final/`; offline simulations and data-collection notebooks are in `strategy_checker/`.

## Features

- Engulfing, Three Soldiers, Hammer, and Shooting Star signal checks in the exchange runner.
- Spot price and balance queries, market/limit order submission code, and account summaries.
- CSV-based strategy simulations and exploratory BingX/Binance data collection.

## Installation

With Python 3.10-3.12, run from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r bingx/final/requirements.txt
```

The BingX connector is bundled with the project; a separate `python-bingx` installation is not required. The requirements include `python-dotenv` for loading local credentials.

## Configuration

Use [`.env.example`](.env.example) as the template for a `.env` file in the repository root. Set both credential variables:

- `BINGX_API_KEY`: your BingX API key.
- `BINGX_SECRET_KEY`: the corresponding secret key.

Alternatively, export these variables in the shell before starting Python or Jupyter. Existing environment variables take precedence over `.env`. The exchange runner and data-gathering notebook reject missing or blank credentials before creating an API client. Local `.env` files are ignored by Git; the sample contains no credentials.

**Credential warning:** Previously committed keys remain in Git history. Revoke or rotate any real exposed keys and do not commit replacement credentials.

## Exchange Runner

Review these files before starting:

- `bingx/final/pairs.txt`: one trading pair per line, currently `BTC-USDT`.
- `bingx/final/interval.txt`: candle interval, currently `3m`.
- `bingx/final/BTClib/constants.py`: signal thresholds and order-sizing parameters.

`DEBUG_MODE` in `bingx/final/BTClib/other.py` defaults to `True`, suppressing order submission and startup cancellation. It still queries the live API and account balances; this is not a sandbox. Setting it to `False` enables real orders and cancels all open spot orders at startup. Review the trading logic before using a funded account.

After configuring credentials locally, run from `bingx/final/` so relative paths resolve correctly:

```bash
cd bingx/final
python finalBTC.py
```

The runner loops until interrupted with `Ctrl+C` and overwrites `summary.txt` with account balances after each cycle.

## Offline Strategy Checks

`strategy_checker/strategy_checker_spot.py` simulates trades without submitting exchange orders. Historical CSV data is not included. Set its `file` variable to your data path and review the CSV-loading logic: it expects `Date`, `Open`, `High`, `Low`, and `Close` columns, newest-first rows, and, by default, an extra row before the column header.

From the repository root, with the virtual environment active:

```bash
python -m pip install matplotlib
cd strategy_checker
python strategy_checker_spot.py
```

The default CSV path is `../../data/csv/Binance_BTCUSDT_2024_minute_2024_04_02.csv`, relative to the working directory. The notebooks can be opened with Jupyter (`python -m pip install notebook`). `dataGatherer.ipynb` additionally imports `binance_historical_data` and uses the same credential variables as the runner. Start its kernel in the repository root or `strategy_checker/` so it can find the root `.env`. It makes network and authenticated account requests, so review its cells before running. The simulation script and notebook differ, and their results are not validated performance benchmarks.

## License

The bundled [python-bingx](https://github.com/niewiemczego/python-bingx) connector identifies itself as MIT-licensed in its metadata. No project-level license file is included.
