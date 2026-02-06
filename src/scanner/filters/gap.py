import polars as pl
from typing import List
from src.scanner.filters.base import BaseFilter


class GapUpFilter(BaseFilter):
    def __init__(self, threshold_pct: float):
        """
        Filter stocks that gapped up.
        Logic: Open > PrevHigh * (1 + threshold_pct / 100)
        """
        self.threshold_pct = threshold_pct

    def required_indicators(self) -> List[pl.Expr]:
        # We need the previous day's high
        prev_high = pl.col("high").shift(1).over("symbol").alias("prev_high")
        return [prev_high]

    def apply(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        threshold_factor = 1 + (self.threshold_pct / 100)
        return lf.filter(pl.col("open") > pl.col("prev_high") * threshold_factor)
