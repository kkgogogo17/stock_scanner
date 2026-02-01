import polars as pl
from pathlib import Path
from src.config import DAILY_DATA_DIR
from src.indicators.technical import add_common_indicators


class ScannerEngine:
    def __init__(self, data_dir: Path = DAILY_DATA_DIR):
        self.data_dir = data_dir

    def scan(
        self,
        min_price: float = None,
        min_volume: float = None,
        min_relative_volume: float = None,
        min_adr: float = None,
        trend_template: bool = False,
        rsi_threshold: float = None,
    ) -> pl.DataFrame:
        """
        Scan all parquet files for stocks matching criteria.
        Uses LazyFrames for efficiency.
        """
        # Scan all parquet files in the daily directory
        try:
            lf = pl.scan_parquet(
                str(self.data_dir / "*.parquet"), include_file_paths="file_path"
            )
        except Exception:
            return pl.DataFrame()

        # Extract symbol
        lf = lf.with_columns(
            pl.col("file_path")
            .str.split("/")
            .list.last()
            .str.replace(".parquet", "")
            .alias("symbol")
        )

        # Sort by symbol and date
        lf = lf.sort(["symbol", "date"])

        # Base Indicators used in simple filters
        # Note: We group complex indicators to avoid clutter if not needed, 
        # but for LazyFrame it's lazily evaluated anyway.
        
        # Calculate Rolling metrics with .over("symbol")
        # We need SMA50, SMA150, SMA200 for Trend Template
        # We need 52-week High/Low (252 days) for Trend Template
        # We need ADR(20) for volatility filter
        
        # Define expressions for window functions
        window_exprs = [
            pl.col("close").rolling_mean(50).over("symbol").alias("sma_50"),
            pl.col("close").rolling_mean(150).over("symbol").alias("sma_150"),
            pl.col("close").rolling_mean(200).over("symbol").alias("sma_200"),
            pl.col("volume").rolling_mean(20).over("symbol").alias("avg_volume_20"),
        ]

        if trend_template or min_adr is not None:
             # Add specific indicators if requested
            window_exprs.extend([
                pl.col("high").rolling_max(252).over("symbol").alias("high_252"),
                pl.col("low").rolling_min(252).over("symbol").alias("low_252"),
            ])
            
            # ADR Calculation involves a prior step (daily range), so we might need a 2-step approach
            # or use a complex expression.
            # Daily Range % = (High - Low) / Low * 100
            daily_range_pct = (pl.col("high") - pl.col("low")) / pl.col("low") * 100
            window_exprs.append(
                 daily_range_pct.rolling_mean(20).over("symbol").alias("adr_20")
            )

        lf = lf.with_columns(window_exprs)

        # RVOL Calculation
        lf = lf.with_columns(
            (pl.col("volume") / pl.col("avg_volume_20")).alias("rvol_20")
        )
        
        # Trend Template "SMA200 trending up" check:
        # Current SMA200 > SMA200 20 days ago (approx 1 month)
        if trend_template:
            lf = lf.with_columns(
                pl.col("sma_200").shift(20).over("symbol").alias("sma_200_1m_ago")
            )

        # Filter: Last row per symbol
        lf = lf.group_by("symbol").last()

        # Apply Screening Criteria
        if min_price is not None:
            lf = lf.filter(pl.col("close") >= min_price)

        if min_volume is not None:
            lf = lf.filter(pl.col("volume") >= min_volume)

        if min_relative_volume is not None:
            lf = lf.filter(pl.col("rvol_20") >= min_relative_volume)

        if min_adr is not None:
            lf = lf.filter(pl.col("adr_20") >= min_adr)

        if trend_template:
            # Minervini Trend Template Criteria:
            # 1. Price > SMA50 > SMA150 > SMA200
            # 2. SMA200 is trending up (Current > 1 month ago)
            # 3. Price > 52-week Low + 25% (1.25 * Low)
            # 4. Price within 25% of 52-week High (Price > 0.75 * High) 
            #    (Note: "Near highs" usually means within 15-25% pullback)
            
            lf = lf.filter(
                (pl.col("close") > pl.col("sma_50")) &
                (pl.col("sma_50") > pl.col("sma_150")) &
                (pl.col("sma_150") > pl.col("sma_200")) &
                (pl.col("sma_200") > pl.col("sma_200_1m_ago")) &
                (pl.col("close") > (pl.col("low_252") * 1.25)) &
                (pl.col("close") > (pl.col("high_252") * 0.75)) 
            )

        # Collect result
        return lf.collect()
