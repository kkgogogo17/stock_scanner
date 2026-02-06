import polars as pl
from pathlib import Path
from typing import List
from src.config import DAILY_DATA_DIR
from src.scanner.filters.base import BaseFilter


class ScannerEngine:
    def __init__(self, data_dir: Path = DAILY_DATA_DIR):
        self.data_dir = data_dir

    def scan(self, filters: List[BaseFilter]) -> pl.DataFrame:
        """
        Scan all parquet files for stocks matching criteria.
        Uses LazyFrames for efficiency.
        Accepts a list of Filter objects to apply.
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

        # 1. Collect all required indicators from filters
        # Use a dict/set to deduplicate based on expression string representation if needed,
        # but Polars optimizer is generally good at this.
        # We will simply collect all and let Polars optimize, or we can try to be smarter.
        # For now, let's just flatten the list.
        
        indicators = []
        for f in filters:
            indicators.extend(f.required_indicators())

        # If we have indicators, apply them
        if indicators:
            # Basic dedup by string representation might be useful to avoid clutter
            # but simplest is just passing them.
            lf = lf.with_columns(indicators)

        # 2. Filter: Last row per symbol
        # We must do this *after* rolling calculations (which happen in with_columns/over)
        # but *before* applying simple scalar filters usually.
        # However, our filters might need history? No, filters usually apply to the *current* state (last row).
        # Standard scanner logic: Calculate indicators on full history -> Take last row -> Check criteria.
        
        lf = lf.group_by("symbol").last()

        # 3. Apply Filters
        for f in filters:
            lf = f.apply(lf)

        # Collect result
        return lf.collect()
