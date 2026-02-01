import polars as pl
import pandas as pd
import re
from lightweight_charts import Chart
from datetime import timedelta


class Plotter:
    def __init__(self):
        pass

    def _process_data(
        self, df: pl.DataFrame, resample: str = "1d", period: str | None = None
    ) -> pd.DataFrame:
        """
        Helper method to filter and resample data.
        Returns a Pandas DataFrame ready for Lightweight Charts.
        """
        # 1. Filter by period
        if period:
            end_date = df["date"].max()
            start_date = self._calculate_start_date(end_date, period)
            df = df.filter(pl.col("date") >= start_date)

        # 2. Resample if needed (Polars)
        if resample:
            df = df.sort("date")
            q = df.group_by_dynamic("date", every=resample).agg(
                [
                    pl.col("open").first(),
                    pl.col("high").max(),
                    pl.col("low").min(),
                    pl.col("close").last(),
                    pl.col("volume").sum(),
                ]
            )
            df = q.collect() if isinstance(q, pl.LazyFrame) else q

        # 3. Prepare for Lightweight Charts
        pdf = df.to_pandas()

        if "date" in pdf.columns:
            pdf = pdf.rename(columns={"date": "time"})

        pdf = pdf.sort_values("time")
        pdf["time"] = pd.to_datetime(pdf["time"]).astype("datetime64[ns]")

        return pdf

    def _add_series_to_chart(
        self,
        chart_obj,
        df: pl.DataFrame,
        symbol: str,
        resample: str = "1d",
        period: str | None = None,
    ):
        """
        Helper to add Candle + SMA series to a chart object (Main chart or Subchart).
        """
        # 1. Process Data
        pdf = self._process_data(df, resample, period)

        # 2. Configure Chart Legend
        chart_obj.legend(visible=True)

        # 3. Set Candle Data
        chart_obj.set(pdf)

        # 4. Indicators
        if len(pdf) > 50:
            sma50 = pdf["close"].rolling(window=50).mean()
            line50 = chart_obj.create_line(
                name="SMA 50", color="rgba(255, 235, 59, 0.7)"
            )
            line50.set(pd.DataFrame({"time": pdf["time"], "SMA 50": sma50}).dropna())

        if len(pdf) > 200:
            sma200 = pdf["close"].rolling(window=200).mean()
            line200 = chart_obj.create_line(
                name="SMA 200", color="rgba(255, 255, 255, 0.5)"
            )
            line200.set(pd.DataFrame({"time": pdf["time"], "SMA 200": sma200}).dropna())

    def plot_candle(
        self,
        ticker_data: list[tuple[str, pl.DataFrame]],
        resample: str = "1d",
        period: str | None = None,
    ):
        """
        Plot interactive candlestick chart(s) using Lightweight Charts.
        Supports multiple tickers as subcharts.

        Args:
            ticker_data: List of (symbol, DataFrame) tuples.
            resample: Resample frequency.
            period: Lookback period.
        """
        if not ticker_data:
            return

        # 1. Initialize Main Window
        # Use the first ticker for the window title
        first_symbol, _ = ticker_data[0]
        if len(ticker_data) > 1:
            chart = Chart(
                title=f"{first_symbol} - {resample if resample else 'Daily'}",
                toolbox=True,
                inner_width=0.5,
                inner_height=0.5,
            )
        else:
            chart = Chart(
                title=f"{first_symbol} - {resample if resample else 'Daily'}",
                toolbox=True,
                width=1200,
                height=800,
            )

        # Style (Dark Mode) - Applies to the whole window
        chart.layout(background_color="#131722", text_color="#d1d4dc")
        chart.candle_style(up_color="#2962ff", down_color="#e91e63")

        # 2. Add First Ticker to Main Chart
        self._add_series_to_chart(
            chart, ticker_data[0][1], ticker_data[0][0], resample, period
        )
        chart.watermark(first_symbol)

        # 3. Add Subsequent Tickers as Subcharts
        for symbol, df in ticker_data[1:]:
            # Create subchart
            # width=1.0 means full width, height=0.5 is relative ratio, but sync logic handles it
            subchart = chart.create_subchart(position="right", width=0.5, height=0.5)
            subchart.watermark(symbol)
            subchart.layout(background_color="#131722", text_color="#d1d4dc")
            subchart.candle_style(up_color="#2962ff", down_color="#e91e63")

            # Apply same style to subchart if possible, or just add series
            # lightweight-charts subcharts usually inherit layout, but series styles need setting
            # We call our helper which sets the data and indicators
            self._add_series_to_chart(subchart, df, symbol, resample, period)

        # 4. Show Window
        chart.show(block=True)

    def _calculate_start_date(self, end_date, period: str):
        # specific parsing for period string
        # simple implementation
        match = re.match(r"(\d+)([a-z]+)", period)
        if not match:
            return end_date - timedelta(days=365)  # default 1y fallback

        val, unit = int(match.group(1)), match.group(2)

        if unit.startswith("y"):
            days = val * 365
        elif unit.startswith("m"):  # month
            days = val * 30
        elif unit.startswith("w"):
            days = val * 7
        elif unit.startswith("d"):
            days = val
        else:
            days = 365

        return end_date - timedelta(days=days)
