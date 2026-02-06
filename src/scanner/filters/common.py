import polars as pl
from typing import List
from src.scanner.filters.base import BaseFilter


class MinPriceFilter(BaseFilter):
    def __init__(self, min_price: float):
        self.min_price = min_price

    def required_indicators(self) -> List[pl.Expr]:
        return []

    def apply(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        return lf.filter(pl.col("close") >= self.min_price)


class MinVolumeFilter(BaseFilter):
    def __init__(self, min_volume: float):
        self.min_volume = min_volume

    def required_indicators(self) -> List[pl.Expr]:
        return []

    def apply(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        return lf.filter(pl.col("volume") >= self.min_volume)


class MinRVolFilter(BaseFilter):
    def __init__(self, min_rvol: float, period: int = 20):
        self.min_rvol = min_rvol
        self.period = period

    def required_indicators(self) -> List[pl.Expr]:
        # We need rvol calculation
        # rvol_20 = volume / sma(volume, 20)

        # Define the expression for Average Volume
        avg_vol_expr = pl.col("volume").rolling_mean(self.period).over("symbol")

        # Return two expressions:
        # 1. The Average Volume column itself (useful to see)
        # 2. The RVOL column (calculated using the expression, NOT by referencing the column name)
        #    This ensures we don't hit "Column not found" errors in a single with_columns() call.
        return [
            avg_vol_expr.alias(f"avg_volume_{self.period}"),
            (pl.col("volume") / avg_vol_expr).alias(f"rvol_{self.period}"),
        ]

    def apply(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        return lf.filter(pl.col(f"rvol_{self.period}") >= self.min_rvol)


class MinAdrFilter(BaseFilter):
    def __init__(self, min_adr: float, period: int = 20):
        self.min_adr = min_adr
        self.period = period

    def required_indicators(self) -> List[pl.Expr]:
        # Daily Range % = (High - Low) / Low * 100
        daily_range_pct = (pl.col("high") - pl.col("low")) / pl.col("low") * 100
        adr = (
            daily_range_pct.rolling_mean(self.period)
            .over("symbol")
            .alias(f"adr_{self.period}")
        )
        return [adr]

    def apply(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        return lf.filter(pl.col(f"adr_{self.period}") >= self.min_adr)
