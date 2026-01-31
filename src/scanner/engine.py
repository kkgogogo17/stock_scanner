import polars as pl
from pathlib import Path
from src.config import DAILY_DATA_DIR
from src.indicators.technical import add_common_indicators

class ScannerEngine:
    def __init__(self, data_dir: Path = DAILY_DATA_DIR):
        self.data_dir = data_dir

    def scan(self, min_price: float = None, min_volume: float = None, rsi_threshold: float = None) -> pl.DataFrame:
        """
        Scan all parquet files for stocks matching criteria.
        Uses LazyFrames for efficiency.
        """
        # Scan all parquet files in the daily directory
        # We assume file name matches Ticker.parquet
        # include_file_paths="file_path" allows us to extract the ticker later
        
        try:
            lf = pl.scan_parquet(str(self.data_dir / "*.parquet"), include_file_paths="file_path")
        except Exception:
            # Handle case where no files exist
            return pl.DataFrame()

        # Extract symbol from filename (e.g. ".../AAPL.parquet" -> "AAPL")
        # Note: This regex depends on the OS path separator, but simplest is to split string
        lf = lf.with_columns(
            pl.col("file_path").str.split("/").list.last().str.replace(".parquet", "").alias("symbol")
        )

        # Optimization: Filter by Date FIRST to reduce processing
        # We usually only care about the LATEST available data point for scanning
        # But since different stocks might have different "last dates" (delisted vs active),
        # we can't just pick "today".
        # Strategy:
        # 1. Calculate indicators on the full history (needed for SMA200 etc)
        # 2. Filter for the last row PER SYMBOL
        
        # Sort by symbol and date
        lf = lf.sort(["symbol", "date"])

        # Add Indicators
        # Note: Rolling windows in Polars require correct ordering.
        # We must group_by("symbol") to calculate indicators per stock correctly.
        # However, group_by on LazyFrame can be expensive if not careful.
        # But 'rolling' expressions in Polars 1.0+ often handle grouping implicitly if specified,
        # or we use `.over("symbol")`.
        
        # Using .over("symbol") is the performant way to do window functions in Polars
        lf = lf.with_columns([
            pl.col("close").rolling_mean(window_size=50).over("symbol").alias("sma_50"),
            pl.col("close").rolling_mean(window_size=200).over("symbol").alias("sma_200"),
            # RSI logic needs to be adapted for .over() or implemented inside
            # For simplicity in this MVP, let's use a simplified approach or re-use the function carefully.
            # We'll inline the simple filters first.
        ])
        
        # For RSI, it's complex to implement efficiently with .over() using standard simple expressions 
        # because of the recursive nature of EMA/RSI. 
        # For MVP, we might skip RSI in the "Lazy Global Scan" or strictly use `map_groups` (slower).
        # OR: We filter down to the last N days first? No, we need history for RSI.
        
        # Let's stick to Simple filters for MVP speed: Price, Volume, SMA.
        
        # Filter: Last row per symbol
        # We can use `group_by(symbol).last()`
        # But we need the indicators calculated BEFORE taking the last row.
        
        # 1. Calc Indicators (SMA only for now to ensure speed)
        # Already done above with .over()
        
        # 2. Filter for last date
        lf = lf.group_by("symbol").last()
        
        # 3. Apply Screening Criteria
        if min_price is not None:
            lf = lf.filter(pl.col("close") >= min_price)
            
        if min_volume is not None:
            lf = lf.filter(pl.col("volume") >= min_volume)
            
        # Example: Golden Cross (SMA50 > SMA200)
        # lf = lf.filter(pl.col("sma_50") > pl.col("sma_200"))
        
        # Collect result
        return lf.collect()
