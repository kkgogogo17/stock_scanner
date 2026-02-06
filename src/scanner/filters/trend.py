import polars as pl
from typing import List
from src.scanner.filters.base import BaseFilter


class TrendTemplateFilter(BaseFilter):
    def required_indicators(self) -> List[pl.Expr]:
        # Required for Minervini Trend Template:
        # SMA 50, 150, 200
        # SMA 200 1 month ago (shift 20)
        # 52-week Low (low_252)
        # 52-week High (high_252)

        return [
            pl.col("close").rolling_mean(50).over("symbol").alias("sma_50"),
            pl.col("close").rolling_mean(150).over("symbol").alias("sma_150"),
            pl.col("close").rolling_mean(200).over("symbol").alias("sma_200"),
            pl.col("low").rolling_min(252).over("symbol").alias("low_252"),
            pl.col("high").rolling_max(252).over("symbol").alias("high_252"),
            # For "SMA200 trending up", we need the shifted value.
            # However, we can only shift *after* sma_200 is available if we do it in one pass,
            # or we can define it as a nested expression.
            # In Polars, we can define dependencies.
            pl.col("close").rolling_mean(200).over("symbol").shift(20).over("symbol").alias("sma_200_1m_ago")
        ]

    def apply(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        # Minervini Trend Template Criteria:
        # 1. Price > SMA50 > SMA150 > SMA200
        # 2. SMA200 is trending up (Current > 1 month ago)
        # 3. Price > 52-week Low + 25% (1.25 * Low)
        # 4. Price within 25% of 52-week High (Price > 0.75 * High)

        return lf.filter(
            (pl.col("close") > pl.col("sma_50")) &
            (pl.col("sma_50") > pl.col("sma_150")) &
            (pl.col("sma_150") > pl.col("sma_200")) &
            (pl.col("sma_200") > pl.col("sma_200_1m_ago")) &
            (pl.col("close") > (pl.col("low_252") * 1.25)) &
            (pl.col("close") > (pl.col("high_252") * 0.75))
        )
