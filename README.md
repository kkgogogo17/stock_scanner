
# us-stock-scanner

## CLI Commands

All commands are run via:

```
python3 main.py <command> [options]
```

### `sync`
Fetch daily data for one or more symbols from Tiingo and save to parquet.

```
python3 main.py sync AAPL MSFT TSLA
```

### `sync-all`
Sync all tickers from the maintained universe that meet the 2-month dollar volume filter.

```
python3 main.py sync-all
```

### `list-data`
List all locally available tickers (parquet files).

```
python3 main.py list-data
```

### `scan`
Scan local data for stocks matching criteria.

Options:
- `--min-price` Minimum close price
- `--min-volume` Minimum volume
- `--sort` Column to sort by (default: `symbol`)

```
python3 main.py scan --min-price 10 --min-volume 1000000 --sort close
```

### `plot`
Plot a candlestick chart for a ticker.

Options:
- `--resample` Resample frequency (default: `1d`)
- `--period` Lookback period (omit to plot all data)

```
python3 main.py plot SPY
python3 main.py plot SPY --period 1y --resample 1w
```

### `head`
Show the first N rows of a ticker’s parquet data in a readable table.

Options:
- `--n` Number of rows to display (default: `10`)

```
python3 main.py head SPY --n 10
```
