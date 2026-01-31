# Implementation Plan: US Stock Scanner (Tiingo + Polars)

## Overview
This document outlines the architecture and development steps for a high-performance US Stock Scanner. The system leverages **Tiingo** for institutional-grade data, **Polars** for high-performance data manipulation, and **Parquet** for efficient local storage.

## Requirements
- **Data Source**: Tiingo API (Daily OHLCV).
- **Authentication**: Secure handling of Tiingo API Key via environment variables (`.env`).
- **Data Processing**: Polars (leveraging lazy evaluation) for all transformations and indicator calculations.
- **Storage**: Local Parquet files (partitioned by symbol) for high-speed I/O.
- **Interface**: CLI command to "sync" data and "scan" for setups.

## Architecture

### Directory Structure
```
us_stock_scanner/
├── .env                # API Keys (TIINGO_API_KEY)
├── data/               # Parquet storage (e.g., data/daily/AAPL.parquet)
├── src/
│   ├── __init__.py
│   ├── config.py       # Configuration & Env loading
│   ├── api/
│   │   └── tiingo.py   # Tiingo API client (using requests)
│   ├── storage/
│   │   └── parquet_store.py # Parquet read/write operations (Polars)
│   ├── indicators/
│   │   └── technical.py # Polars-based indicator functions (SMA, RSI, etc.)
│   ├── scanner/
│   │   └── engine.py   # Core scanning logic (LazyFrame filters)
│   └── cli.py          # Entry point (Typer/Argparse)
├── main.py             # Application entry point
├── pyproject.toml      # Dependencies
└── README.md
```

### Key Components
1.  **Tiingo Client**: Fetches historical data. Handles rate limits and pagination.
2.  **Parquet Store**: Manages data persistence. Polars reads Parquet files natively.
3.  **Polars Engine**: The heart of the application. Uses `LazyFrame` to optimize query plans for scanning thousands of tickers.

## Implementation Steps

### Phase 1: Setup & Data Ingestion (Tiingo -> Parquet)
**Goal**: Can fetch data from Tiingo and save it to a local Parquet file.

1.  **Project Init & Dependencies**
    *   Deps: `polars`, `requests`, `pyarrow`, `python-dotenv`, `typer`, `rich`.
    *   File: `pyproject.toml`
2.  **Configuration & Secrets**
    *   Implement `src/config.py` to load `TIINGO_API_KEY`.
3.  **Tiingo Client**
    *   Implement `fetch_daily_history(symbol, start_date)` using `requests`.
    *   Returns: Polars DataFrame.
    *   File: `src/api/tiingo.py`
4.  **Parquet Storage**
    *   Implement `save_ticker_data(symbol, df)` and `load_ticker_data(symbol)`.
    *   File: `src/storage/parquet_store.py`
5.  **Sync Command**
    *   Create CLI command `sync <symbol>` to fetch and save data.
    *   File: `src/cli.py`

### Phase 2: Indicators & Polars Scanner
**Goal**: Calculate indicators efficiently and filter stocks based on criteria.

1.  **Technical Indicators (Polars)**
    *   Implement functions like `calculate_sma(df, period)`, `calculate_rsi(df, period)`.
    *   Must use Polars expressions (`pl.col("close").rolling_mean(...)`).
    *   File: `src/indicators/technical.py`
2.  **Scanner Engine**
    *   Implement `scan_market(criteria)`.
    *   Logic: `pl.scan_parquet` -> Apply Indicators -> Filter -> Collect.
    *   File: `src/scanner/engine.py`

### Phase 3: CLI & Integration
**Goal**: A polished CLI tool to run the entire workflow.

1.  **CLI Polish**
    *   Add `scan` command.
    *   Example: `python main.py scan --strategy "sma_crossover"`.
2.  **Batch Sync**
    *   Support syncing a universe of stocks (e.g., S&P 500 list).

## Risks & Mitigations
- **Rate Limits**: Tiingo has limits (especially for free tier). We will implement backoff/sleep logic.
- **Memory**: Polars `scan_parquet` with `streaming=True` will be used to handle datasets larger than RAM if necessary.
