from abc import ABC, abstractmethod
from typing import List
import polars as pl


class BaseFilter(ABC):
    @abstractmethod
    def required_indicators(self) -> List[pl.Expr]:
        """
        Return a list of Polars expressions (columns) needed for this filter.
        These expressions will be passed to `with_columns` by the engine before filtering.
        """
        pass

    @abstractmethod
    def apply(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        """
        Apply the filtering logic (filter/where clause).
        """
        pass
