# pip install duckdb pandas pyarrow plotly

import duckdb
import pandas as pd
import plotly.graph_objects as go


def load_ohlcv_resampled(
    parquet_path: str, timeframe: str = "15 minutes"
) -> pd.DataFrame:
    """
    parquet 里假设有列：
    symbol, ts(UTC timestamp), open, high, low, close, volume
    timeframe 示例: '5 minutes', '15 minutes', '1 hour', '1 day'
    """
    con = duckdb.connect()

    # DuckDB 用 date_bin 做对齐分桶（更像交易软件的 bar）
    # 注意：date_bin 需要一个 anchor，这里用 epoch
    q = f"""
    WITH base AS (
      SELECT
        symbol,
        ts,
        open, high, low, close,
        volume,
        date_bin(INTERVAL '{timeframe}', ts, TIMESTAMP '1970-01-01') AS bucket
      FROM read_parquet('{parquet_path}')
    ),
    agg AS (
      SELECT
        symbol,
        bucket AS ts,
        arg_min(open, ts)  AS open,
        max(high)          AS high,
        min(low)           AS low,
        arg_max(close, ts) AS close,
        sum(volume)        AS volume
      FROM base
      GROUP BY symbol, bucket
    )
    SELECT * FROM agg
    ORDER BY ts
    """
    df = con.execute(q).df()
    return df


def plot_candles(df: pd.DataFrame, title: str = ""):
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df["ts"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="OHLC",
            ),
            go.Bar(x=df["ts"], y=df["volume"], name="Volume", yaxis="y2", opacity=0.35),
        ]
    )
    fig.update_layout(
        title=title,
        xaxis_rangeslider_visible=False,
        yaxis_title="Price",
        yaxis2=dict(title="Volume", overlaying="y", side="right", showgrid=False),
        hovermode="x unified",
        height=700,
    )
    fig.show()


if __name__ == "__main__":
    df = load_ohlcv_resampled("data/AAPL_1min.parquet", timeframe="15 minutes")
    plot_candles(df, title="AAPL 15m (resampled from 1m)")
