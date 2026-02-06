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
from src.scanner.filters.common import (
    MinPriceFilter,
    MinVolumeFilter,
    MinRVolFilter,
    MinAdrFilter,
)
from src.scanner.filters.trend import TrendTemplateFilter
from src.scanner.filters.gap import GapUpFilter
from src.visualization.plotter import Plotter
from src.scanner.recipe import RecipeManager
from rich.table import Table
from rich.progress import Progress
import concurrent.futures

app = typer.Typer()
console = Console()
store = ParquetStore()
scanner_engine = ScannerEngine()
plotter = Plotter()

TICKER_FILE = Path(__file__).resolve().parent / "data" / "tickers.csv"
VOLUME_THRESHOLD = 150_000_000
LOOKBACK_DAYS = 60
MAX_WORKERS = 32


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


def _sync_one_ticker(symbol: str) -> tuple[str, bool, str, float]:
    """
    Helper function to sync a single ticker.
    Returns: (symbol, success, message, dollar_volume)
    """
    try:
        # Create a new client instance per thread/task to be safe,
        # though requests.Session is generally thread-safe.
        # However, api_key reading might be cleaner this way.
        client = TiingoClient()
        df = client.fetch_daily_history(symbol)

        if df is None or df.is_empty():
            return symbol, False, "Failed to fetch or empty data", 0.0

        dollar_volume = _dollar_volume_last_2_months(df)
        store.save_ticker_data(symbol, df)

        if dollar_volume >= VOLUME_THRESHOLD:
            return symbol, True, "Synced", dollar_volume
        else:
            return (
                symbol,
                True,
                f"Synced (below threshold: ${dollar_volume:,.0f})",
                dollar_volume,
            )

    except Exception as e:
        return symbol, False, str(e), 0.0


@app.command()
def sync(symbols: List[str]):
    """
    Fetch daily data for a list of symbols from Tiingo and save to Parquet.
    Example: python main.py sync AAPL MSFT TSLA
    """
    try:
        # Check API key early
        TiingoClient()
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        console.print("Please set TIINGO_API_KEY in .env file")
        raise typer.Exit(code=1)

    for symbol in track(symbols, description="Syncing data..."):
        symbol = symbol.upper()
        # Use the helper but ignore dollar volume for explicit sync
        _, success, msg, _ = _sync_one_ticker(symbol)
        if success:
            console.print(f"[green]Synced {symbol}[/green]")
        else:
            console.print(f"[red]{msg} {symbol}[/red]")


@app.command()
def sync_all():
    """
    Sync all tickers from the maintained universe concurrently.
    """
    try:
        # Check API key early
        TiingoClient()
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        console.print("Please set TIINGO_API_KEY in .env file")
        raise typer.Exit(code=1)

    tickers = _load_ticker_universe()
    if not tickers:
        console.print("[yellow]No tickers found in the universe list.[/yellow]")
        return

    console.print(
        f"Starting concurrent sync for {len(tickers)} tickers with {MAX_WORKERS} workers..."
    )

    eligible_count = 0

    with Progress() as progress:
        task_id = progress.add_task("Fetching universe...", total=len(tickers))

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(_sync_one_ticker, symbol): symbol for symbol in tickers
            }

            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    sym, success, msg, dollar_vol = future.result()

                    if success:
                        if dollar_vol >= VOLUME_THRESHOLD:
                            eligible_count += 1
                            progress.console.print(f"[green]{msg} {sym}[/green]")
                        else:
                            progress.console.print(f"[yellow]{msg} {sym}[/yellow]")
                    else:
                        progress.console.print(f"[red]{msg} {sym}[/red]")

                except Exception as exc:
                    progress.console.print(
                        f"[red]Generated an exception for {symbol}: {exc}[/red]"
                    )

                progress.advance(task_id)

    if eligible_count == 0:
        console.print(
            "[yellow]No tickers met the 2-month dollar volume threshold.[/yellow]"
        )
    else:
        console.print(
            f"[bold green]Sync complete. {eligible_count} tickers met the volume threshold.[/bold green]"
        )


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
    min_relative_volume: float = typer.Option(
        None, help="Minimum Relative Volume (RVOL)"
    ),
    min_adr: float = typer.Option(None, help="Minimum Average Daily Range (ADR %)"),
    gap_up: float = typer.Option(
        None, help="Minimum Gap Up % (Open > PrevHigh * (1 + gap/100))"
    ),
    trend_template: bool = typer.Option(
        False, help="Filter by Minervini Trend Template"
    ),
    sort: str = typer.Option("symbol", help="Column to sort by"),
    recipe: str = typer.Option(None, help="Load criteria from a recipe file (YAML)"),
    save_recipe: str = typer.Option(
        None, help="Save current criteria to a recipe file"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Run in interactive mode"
    ),
):
    """
    Scan local data for stocks matching criteria.
    """
    # 0. Interactive Mode
    if interactive:
        # Import here to avoid loading UI libs unless needed
        try:
            from src.ui.wizard import run_scan_wizard

            wizard_config = run_scan_wizard()
            # Merge wizard config. Wizard overrides everything else if used.
            # We map wizard keys to local variables.
            if wizard_config:
                min_price = wizard_config.get("min_price", min_price)
                min_volume = wizard_config.get("min_volume", min_volume)
                min_relative_volume = wizard_config.get(
                    "min_relative_volume", min_relative_volume
                )
                min_adr = wizard_config.get("min_adr", min_adr)
                gap_up = wizard_config.get("gap_up", gap_up)
                trend_template = wizard_config.get("trend_template", trend_template)
                sort = wizard_config.get("sort", sort)
        except ImportError:
            console.print(
                "[red]Interactive mode requires 'questionary'. Please install it.[/red]"
            )
            return

    # 1. Load Recipe if provided
    loaded_config = {}
    if recipe:
        loaded_config = RecipeManager.load_recipe(recipe)
        if loaded_config:
            console.print(f"[dim]Loaded recipe: {recipe}[/dim]")

    # 2. Merge Configs
    # Precedence: Explicit Arg > Recipe > Default (None/False)
    # We rely on the fact that Typer defaults are None for floats.
    # For booleans (trend_template), the default is False.
    # We check if the argument matches the default to decide whether to use the recipe value.
    # Note: This has a minor edge case where if the user explicitly wants "False" but recipe has "True",
    # and default is "False", we might override.
    # Ideally, we would inspect the click context to see what was actually passed, but simple logic covers 99% of cases.

    if min_price is None and "min_price" in loaded_config:
        min_price = loaded_config["min_price"]

    if min_volume is None and "min_volume" in loaded_config:
        min_volume = loaded_config["min_volume"]

    if min_relative_volume is None and "min_relative_volume" in loaded_config:
        min_relative_volume = loaded_config["min_relative_volume"]

    if min_adr is None and "min_adr" in loaded_config:
        min_adr = loaded_config["min_adr"]

    if gap_up is None and "gap_up" in loaded_config:
        gap_up = loaded_config["gap_up"]

    # Boolean is tricky because default is False.
    # If recipe is True and user didn't specify (still False), we set to True.
    # If user explicitly passed --no-trend-template (if we had it), we would want False.
    # For now, we assume if recipe says True, we enable it unless we can detect explicit disable.
    if trend_template is False and loaded_config.get("trend_template", False):
        trend_template = True

    if sort == "symbol" and "sort" in loaded_config:
        sort = loaded_config["sort"]

    # 3. Save Recipe if requested
    if save_recipe:
        current_config = {
            "min_price": min_price,
            "min_volume": min_volume,
            "min_relative_volume": min_relative_volume,
            "min_adr": min_adr,
            "gap_up": gap_up,
            "trend_template": trend_template,
            "sort": sort,
        }
        # Filter out Nones to keep recipe clean
        current_config = {k: v for k, v in current_config.items() if v is not None}
        RecipeManager.save_recipe(save_recipe, current_config)

    console.print("[bold blue]Running scan...[/bold blue]")

    # Build filter list dynamically
    filters = []

    if min_price is not None:
        filters.append(MinPriceFilter(min_price))

    if min_volume is not None:
        filters.append(MinVolumeFilter(min_volume))

    if min_relative_volume is not None:
        filters.append(MinRVolFilter(min_relative_volume))

    if min_adr is not None:
        filters.append(MinAdrFilter(min_adr))

    if gap_up is not None:
        filters.append(GapUpFilter(gap_up))

    if trend_template:
        filters.append(TrendTemplateFilter())

    try:
        results = scanner_engine.scan(filters)
    except Exception as e:
        console.print(f"[red]Error during scan: {e}[/red]")
        # Print full traceback for debugging if needed, but simple error is user friendly
        import traceback

        traceback.print_exc()
        return

    if results.is_empty():
        console.print("[yellow]No stocks matched the criteria.[/yellow]")
        return

    # Sort results
    if sort in results.columns:
        results = results.sort(
            sort,
            descending=True
            if sort in ["close", "volume", "rvol_20", "adr_20"]
            else False,
        )

    # Display Table
    table = Table(title=f"Scan Results ({len(results)} matches)")
    table.add_column("Symbol", style="cyan", no_wrap=True)
    table.add_column("Date", style="magenta")
    table.add_column("Close", justify="right", style="green")
    table.add_column("Volume", justify="right")
    table.add_column("RVOL", justify="right")
    table.add_column("ADR%", justify="right")
    table.add_column("SMA50", justify="right")
    table.add_column("SMA200", justify="right")

    for row in results.iter_rows(named=True):
        table.add_row(
            row["symbol"],
            str(row["date"]),
            f"${row['close']:.2f}",
            f"{row['volume']:,}",
            f"{row.get('rvol_20', 0):.2f}" if row.get("rvol_20") else "-",
            f"{row.get('adr_20', 0):.2f}%" if row.get("adr_20") else "-",
            f"{row.get('sma_50', 0):.2f}" if row.get("sma_50") else "-",
            f"{row.get('sma_200', 0):.2f}" if row.get("sma_200") else "-",
        )

    console.print(table)


@app.command()
def plot(
    tickers: List[str],
    resample: str = typer.Option(
        "1d", help="Resample frequency (e.g., '1w', '1mo'). Default: Daily"
    ),
    period: str = typer.Option(
        None, help="Lookback period (e.g., '1y', '6mo'). Omit for all data"
    ),
):
    """
    Plot Candlestick chart(s).
    If multiple tickers are provided, they are shown as separate subcharts in one window.
    Example: python main.py plot AAPL MSFT
    """
    if not tickers:
        console.print("[red]Please provide at least one ticker.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[bold blue]Plotting {', '.join(tickers)}...[/bold blue]")

    ticker_data = []

    # 1. Load data for all tickers
    for ticker in tickers:
        ticker = ticker.upper()
        try:
            df = store.load_ticker_data(ticker)
            ticker_data.append((ticker, df))
        except FileNotFoundError:
            console.print(
                f"[yellow]No data found for {ticker}. Please run 'sync {ticker}' first. Skipping.[/yellow]"
            )

    if not ticker_data:
        console.print("[red]No valid data loaded for any provided tickers.[/red]")
        raise typer.Exit(code=1)

    # 2. Plot
    try:
        plotter.plot_candle(ticker_data, resample=resample, period=period)
    except Exception as e:
        console.print(f"[red]Error plotting: {e}[/red]")
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
