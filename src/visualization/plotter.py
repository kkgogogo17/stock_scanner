import polars as pl
import pandas as pd
import re
from lightweight_charts import Chart
from datetime import timedelta


class Plotter:
    def __init__(self):
        pass

    def plot_candle(
        self, df: pl.DataFrame, symbol: str, resample: str = "1d", period: str = "1y"
    ):
        """
        Plot interactive candlestick chart using Lightweight Charts.

        Args:
            df: Polars DataFrame with columns [date, open, high, low, close, volume]
            symbol: Ticker symbol
            resample: Resample frequency (e.g., '1w', '1mo'). None means daily.
            period: Lookback period (e.g., '1y', '6mo'). Default '1y'.
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
        # Ensure we have a Pandas DataFrame.
        pdf = df.to_pandas()

        # FIX: Rename 'date' to 'time'
        if "date" in pdf.columns:
            pdf = pdf.rename(columns={"date": "time"})

        # FIX 2: Sort by time (Critical for charts)
        pdf = pdf.sort_values("time")

        # FIX 3: Ensure time is datetime64[ns]; chart library assumes ns before /1e9.
        pdf["time"] = pd.to_datetime(pdf["time"]).astype("datetime64[ns]")

        # 4. Configure Chart
        chart = Chart(
            title=f"{symbol} - {resample if resample else 'Daily'}",
            toolbox=True,
            width=1200,
            height=800,
        )
        chart.legend(visible=True)

        # Style (Dark Mode)
        chart.layout(background_color="#131722", text_color="#d1d4dc")
        chart.candle_style(up_color="#2962ff", down_color="#e91e63")

        # Set Data (expects columns: time, open, high, low, close, volume)
        chart.set(pdf)

        # 5. Indicators (calculate in Pandas)
        Note: We need to handle potential small datasets
        if len(pdf) > 50:
            sma50 = pdf["close"].rolling(window=50).mean()
            line50 = chart.create_line(name="SMA 50", color="rgba(255, 235, 59, 0.7)")
            line50.set(pd.DataFrame({"time": pdf["time"], "SMA 50": sma50}).dropna())

        if len(pdf) > 200:
            sma200 = pdf["close"].rolling(window=200).mean()
            line200 = chart.create_line(
                name="SMA 200", color="rgba(255, 255, 255, 0.5)"
            )
            line200.set(pd.DataFrame({"time": pdf["time"], "SMA 200": sma200}).dropna())

        # 6. Show Window
        # Block execution so the script doesn't exit immediately
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
