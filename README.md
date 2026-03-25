# pysystemtrade

Systematic futures trading in python, using the systems developed by [Rob Carver](https://github.com/robcarver17/)

## Description

**pysystemtrade** is the open source version of Rob Carver's own backtesting and trading engine that implements systems according to the framework outlined in his book ["Systematic Trading"](https://www.systematicmoney.org/systematic-trading), which is further developed on [his blog](https://qoppac.blogspot.com) and in his [other books](https://www.systematicmoney.org/).

For a longer explanation of the motivation and point of this project see this [blog post.](https://qoppac.blogspot.com/2015/12/pysystemtrade.html)

Pysystemtrade is a....:
- Backtesting environment that Rob uses to test all the strategies in his various [books](https://www.systematicmoney.org)
- Which implements all the optimisation and system design principles in his books and on his blog.
- A fully automated system for futures trading (for interactive brokers)

pysystemtrade uses the [IB insync library](https://ib-insync.readthedocs.io/api.html) to connect to interactive brokers.

## History

[Rob](https://github.com/robcarver17/) originally developed and open sourced the system in December 2015. In 2024 [Andy Geach](https://github.com/bug-or-feature) took over as primary maintainer of the project. In January 2026 Rob moved pysystemtrade to a new github "organisation", [pst-group](https://github.com/pst-group). The organisation is 'owned' by Andy and Rob. It is the intention that this organisation will always have at least two owners, which will ensure the project continues into the future in the event of Rob's demise or him losing his github token. 


## Use and documentation

[Introduction (start here)](docs/introduction.md)

[Backtesting user guide](docs/backtesting.md)

[Working with futures data](/docs/data.md)

[Connecting to interactive brokers](/docs/IB.md)

[Running as a production system](/docs/production.md)
 

## Dependencies

See the `project.dependencies` section in [pyproject.toml](pyproject.toml) for full details.


## Installation

This package isn't hosted on pypi.org. So to get the code the easiest way is to use git:

```
# clone the repo to your local filesystem
$ git clone https://github.com/pst-group/pysystemtrade.git

# navigate to the project directory
$ cd pysystemtrade

# either install pysystemtrade normally
$ python -m pip install .

# or install in editable mode, with development dependencies 
$ python -m pip install --editable '.[dev]'
```

There is a more complete installation guide [here](docs/installation.md)

### A note on support

This is an open source project, designed for people who are already comfortable using and writing python code, are capable of installing the dependencies, and who want a head start on implementing a system of their own.  If you need a higher level of support then you are better off with another project. The most efficient way of getting support is by [opening an issue on github](https://github.com/pst-group/pysystemtrade/issues/new). If you discover a bug please include:

- The full script that produces the error, including all `import` statements, or if it's a standard example file a pointer to the file. Ideally this should be a "minimal example" - the shortest possible script that produces the problem.
- Versions of any necessary libraries you have installed
- The full output trace including the error messages

If you have a question like 'how to do X' or 'should we do Y' use the [discussions board](https://github.com/pst-group/pysystemtrade/discussions), not the error reporting. Offers to contribute will of course be gratefully accepted.


## A-Stock Data Module

This fork extends pysystemtrade with a complete **A-share (China) equity data layer** — API client, storage backends, universe management, scheduled fetching, and a `simData` interface for backtesting Chinese stocks.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      simData Interface                       │
│              sysdata/sim/astock_sim_data.py                  │
│         (AStockSimData — drop-in for System())               │
├──────────────┬──────────────┬───────────────┬───────────────┤
│  Daily Prices│ Minute Prices│  Instruments  │  Spread Costs │
├──────────────┴──────────────┴───────────────┴───────────────┤
│                  db_config.py (Backend Switch)                │
│            ASTOCK_BACKEND = parquet | pg                      │
├──────────────────────────┬──────────────────────────────────┤
│   Parquet Backend        │   PostgreSQL Backend              │
│   astock_prices.py       │   astock_pg.py                   │
│   astock_instruments.py  │   (5 tables, UPSERT, indexes)    │
├──────────────────────────┴──────────────────────────────────┤
│                  xiximiao_client.py                           │
│        (Tushare-compatible API, pagination, retry)           │
├─────────────────────────────────────────────────────────────┤
│   universe.py          │  china_calendar.py                  │
│   (SSE50/HS300/ZZ500/  │  (Trading hours, holidays,         │
│    ETF/full market)    │   fetch window, smart sleep)        │
├─────────────────────────────────────────────────────────────┤
│                    fetcher.py (CLI + Scheduler)               │
│   --once/--scan/--force | --backend pg/parquet               │
│   --universe all/valid  | --status/--info/--sync-config      │
│              pm2-managed continuous loop                      │
└─────────────────────────────────────────────────────────────┘
```

### Key Files

| File | Description |
|------|-------------|
| `sysdata/astock/xiximiao_client.py` | API client for xiximiao.com (Tushare proxy). Pagination, smart rate-limit retry (parses API cooldown seconds). |
| `sysdata/astock/astock_prices.py` | Parquet-based daily & minute price storage |
| `sysdata/astock/astock_instruments.py` | CSV-based instrument metadata & spread costs |
| `sysdata/astock/astock_pg.py` | PostgreSQL storage backend (interface-compatible with Parquet) |
| `sysdata/astock/db_config.py` | Backend switch (`ASTOCK_BACKEND` env), SQLAlchemy engine, factory functions |
| `sysdata/astock/universe.py` | Stock pool management: SSE50, HS300, ZZ500, Popular, ETF, full market (~12000 codes) |
| `sysdata/astock/china_calendar.py` | A-share market calendar: trading hours, holidays 2024-2027, fetch window |
| `sysdata/sim/astock_sim_data.py` | `simData` subclass for backtesting A-shares with pysystemtrade's System |
| `sysinit/astock/fetcher.py` | Scheduled data fetcher: incremental updates, market scan, config auto-sync |
| `sysinit/astock/init_pg.py` | PostgreSQL init: create DB/tables, Parquet→PG migration, verification |
| `ecosystem.config.js` | pm2 process config for the fetcher daemon |

### Quick Start

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your XIXIMIAO_TOKEN

# 2. Install dependencies
pip install psycopg2-binary python-dotenv

# 3a. Fetch data (Parquet backend, default)
python -m sysinit.astock.fetcher --once --freq daily --universe popular

# 3b. Or use PostgreSQL backend
python -m sysinit.astock.init_pg --all          # create DB + tables + migrate
# Edit .env: ASTOCK_BACKEND=pg
python -m sysinit.astock.fetcher --once --freq daily --universe all --backend pg

# 4. Run backtest
python -c "
from sysdata.sim.astock_sim_data import AStockSimData
from systems.basesystem import System
from systems.rawdata import RawData
from systems.provided.rules.ewmac import ewmac_calc_vol
from systems.forecasting import Rules
from sysdata.config.configdata import Config

data = AStockSimData()
rules = Rules(dict(ewmac8=dict(function=ewmac_calc_vol, other_args=dict(Lfast=8, Lslow=32))))
system = System([RawData(), rules], data=data)
print(system.rules.get_raw_forecast('600519.SH', 'ewmac8').tail())
"
```

### Data Backend Switch

Set `ASTOCK_BACKEND` in `.env` or pass `--backend` to the fetcher:

| Value | Backend | Storage |
|-------|---------|---------|
| `parquet` (default) | Local Parquet files | `data/astock/daily_prices_parquet/` |
| `pg` | PostgreSQL | Database `astock`, 5 tables |

### Fetcher CLI

```bash
# Market status
python -m sysinit.astock.fetcher --status

# Data info
python -m sysinit.astock.fetcher --info

# One-shot fetch
python -m sysinit.astock.fetcher --once --freq daily --universe popular

# Scan full market for valid symbols
python -m sysinit.astock.fetcher --scan --universe full

# Continuous daemon (pm2)
pm2 start ecosystem.config.js

# Sync instrument config from stored data
python -m sysinit.astock.fetcher --sync-config
```

### PostgreSQL Management

```bash
python -m sysinit.astock.init_pg --create-db       # Create database
python -m sysinit.astock.init_pg --create-tables    # Create tables
python -m sysinit.astock.init_pg --migrate          # Migrate Parquet → PG
python -m sysinit.astock.init_pg --verify           # Verify PG vs Parquet
python -m sysinit.astock.init_pg --stats            # Show table statistics
python -m sysinit.astock.init_pg --all              # All of the above
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `XIXIMIAO_TOKEN` | *(required)* | API token for xiximiao.com |
| `XIXIMIAO_API_URL` | `http://stk_mins.xiximiao.com/dataapi` | API endpoint |
| `ASTOCK_BACKEND` | `parquet` | Data backend: `parquet` or `pg` |
| `ASTOCK_PG_URL` | `postgresql://user@localhost:5432/astock` | PostgreSQL connection URL |

### Current Data Coverage

- **193 A-share instruments** (SSE + SZSE mainboard + ChiNext + STAR)
- **229,836 daily price rows** (2021-03 ~ present)
- **198 instrument configs** with spread costs
- Auto-refreshed via pm2 fetcher daemon during trading hours


## Licensing and legal stuff

GNU v3
( See [LICENSE](LICENSE) )

Absolutely no warranty is implied with this product. Use at your own risk. No guarantee is provided that it will be profitable, or that it won't lose all your money very quickly, or delete every file on your computer (by the way: it's not *supposed* to do that. Just in case you thought it was). All financial trading offers the possibility of loss. Leveraged trading, such as futures trading, may result in you losing all your money, and still owing more. Backtested results are no guarantee of future performance. The owners of the project can take no responsibility for any losses caused by live trading using pysystemtrade. Use at your own risk. The owners of the project are not currently registered or authorised by any financial regulator. 


