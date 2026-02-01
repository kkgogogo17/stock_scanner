import typer
import polars as pl
from rich.console import Console
from rich.progress import track
from typing import List
from pathlib import Path
from datetime import timedelta
from src.api.tiingo import TiingoClient
from src.storage.parquet_store import ParquetStore
from src.scanner.engine import ScannerEngine
from src.visualization.plotter import Plotter
from rich.table import Table

app = typer.Typer()
console = Console()
store = ParquetStore()
scanner_engine = ScannerEngine()
plotter = Plotter()

TICKER_FILE = Path(__file__).resolve().parent / "data" / "tickers.csv"
VOLUME_THRESHOLD = 150_000_000
LOOKBACK_DAYS = 60


def _load_ticker_universe() -> list[str]:
    if not TICKER_FILE.exists():
        console.print(f"[red]Ticker file not found: {TICKER_FILE}[/red]")
        return []

    tickers = []
    for line in TICKER_FILE.read_text().splitlines():
        symbol = line.strip().upper()
        if not symbol or symbol.startswith("#"):
            continue
        tickers.append(symbol)

    return tickers


def _dollar_volume_last_2_months(df: pl.DataFrame) -> float:
    if df.is_empty():
        return 0.0

    end_date = df["date"].max()
    if end_date is None:
        return 0.0

    start_date = end_date - timedelta(days=LOOKBACK_DAYS)
    recent = df.filter(pl.col("date") >= start_date)
    if recent.is_empty():
        return 0.0

    total = recent.select((pl.col("close") * pl.col("volume")).sum()).item()
    return float(total or 0.0)


@app.command()
def sync(symbols: List[str]):
    """
    Fetch daily data for a list of symbols from Tiingo and save to Parquet.
    Example: python main.py sync AAPL MSFT TSLA
    """
    try:
        client = TiingoClient()
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        console.print("Please set TIINGO_API_KEY in .env file")
        raise typer.Exit(code=1)

    for symbol in track(symbols, description="Syncing data..."):
        symbol = symbol.upper()
        # For MVP, we fetch full history (default start 2000-01-01)
        # Optimization: Check last date in parquet and fetch only new data

        df = client.fetch_daily_history(symbol)
        if df is not None:
            store.save_ticker_data(symbol, df)
            console.print(f"[green]Synced {symbol}[/green]")
        else:
            console.print(f"[red]Failed to fetch {symbol}[/red]")


@app.command()
def sync_all():
    """
    Sync all tickers from the maintained universe, filtered by 2-month dollar volume.
    """
    try:
        client = TiingoClient()
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        console.print("Please set TIINGO_API_KEY in .env file")
        raise typer.Exit(code=1)

    tickers = _load_ticker_universe()
    if not tickers:
        console.print("[yellow]No tickers found in the universe list.[/yellow]")
        return

    eligible = []
    for symbol in track(tickers, description="Fetching universe..."):
        df = client.fetch_daily_history(symbol)
        if df is None or df.is_empty():
            console.print(f"[red]Failed to fetch {symbol}[/red]")
            continue

        dollar_volume = _dollar_volume_last_2_months(df)
        store.save_ticker_data(symbol, df)
        if dollar_volume >= VOLUME_THRESHOLD:
            eligible.append(symbol)
            console.print(f"[green]Synced {symbol}[/green]")
        else:
            console.print(
                f"[yellow]Synced {symbol} (below threshold: ${dollar_volume:,.0f})[/yellow]"
            )

    if not eligible:
        console.print("[yellow]No tickers met the 2-month dollar volume threshold.[/yellow]")


@app.command()
def list_data():
    """List all locally available tickers."""
    tickers = store.list_existing_tickers()
    console.print(f"Found {len(tickers)} tickers locally:")
    console.print(", ".join(tickers))


@app.command()
def scan(
    min_price: float = typer.Option(None, help="Minimum Close Price"),
    min_volume: float = typer.Option(None, help="Minimum Volume"),
    sort: str = typer.Option("symbol", help="Column to sort by"),
):
    """
    Scan local data for stocks matching criteria.
    """
    console.print("[bold blue]Running scan...[/bold blue]")

    try:
        results = scanner_engine.scan(min_price=min_price, min_volume=min_volume)
    except Exception as e:
        console.print(f"[red]Error during scan: {e}[/red]")
        return

    if results.is_empty():
        console.print("[yellow]No stocks matched the criteria.[/yellow]")
        return

    # Sort results
    if sort in results.columns:
        results = results.sort(
            sort, descending=True if sort in ["close", "volume"] else False
        )

    # Display Table
    table = Table(title=f"Scan Results ({len(results)} matches)")
    table.add_column("Symbol", style="cyan", no_wrap=True)
    table.add_column("Date", style="magenta")
    table.add_column("Close", justify="right", style="green")
    table.add_column("Volume", justify="right")
    table.add_column("SMA50", justify="right")
    table.add_column("SMA200", justify="right")

    for row in results.iter_rows(named=True):
        table.add_row(
            row["symbol"],
            str(row["date"]),
            f"${row['close']:.2f}",
            f"{row['volume']:,}",
            f"{row['sma_50']:.2f}" if row["sma_50"] else "-",
            f"{row['sma_200']:.2f}" if row["sma_200"] else "-",
        )

    console.print(table)


@app.command()
def plot(
    ticker: str,
    resample: str = typer.Option(
        "1d", help="Resample frequency (e.g., '1w', '1mo'). Default: Daily"
    ),
    period: str = typer.Option(
        None, help="Lookback period (e.g., '1y', '6mo'). Omit for all data"
    ),
):
    """
    Plot a Candlestick chart for a given ticker.
    """
    ticker = ticker.upper()
    console.print(f"[bold blue]Plotting {ticker}...[/bold blue]")

    # 1. Load data
    df = store.load_ticker_data(ticker)
    if df is None:
        console.print(
            f"[red]No data found for {ticker}. Please run 'sync {ticker}' first.[/red]"
        )
        raise typer.Exit(code=1)

    # 2. Plot
    try:
        plotter.plot_candle(df, ticker, resample=resample, period=period)
    except Exception as e:
        console.print(f"[red]Error plotting {ticker}: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def head(ticker: str, n: int = typer.Option(10, help="Number of rows to display")):
    """
    Show the first N rows of a ticker's parquet data in a readable table.
    """
    ticker = ticker.upper()
    df = store.load_ticker_data(ticker)

    if df.is_empty():
        console.print(f"[yellow]No data found for {ticker}.[/yellow]")
        return

    preview = df.head(n)
    table = Table(title=f"{ticker} - Head {min(n, preview.height)} Rows")

    for col in preview.columns:
        table.add_column(col)

    for row in preview.iter_rows():
        table.add_row(*[str(value) for value in row])

    console.print(table)


if __name__ == "__main__":
    app()
