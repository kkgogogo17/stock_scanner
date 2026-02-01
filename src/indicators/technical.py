import polars as pl


def calculate_sma(
    df: pl.LazyFrame, period: int, col_name: str = "close"
) -> pl.LazyFrame:
    """
    Calculate Simple Moving Average (SMA).
    """
    return df.with_columns(
        pl.col(col_name).rolling_mean(window_size=period).alias(f"sma_{period}")
    )


def calculate_ema(
    df: pl.LazyFrame, period: int, col_name: str = "close"
) -> pl.LazyFrame:
    """
    Calculate Exponential Moving Average (EMA).
    Polars ewm_mean is available on Expr.
    """
    return df.with_columns(
        pl.col(col_name).ewm_mean(span=period, adjust=False).alias(f"ema_{period}")
    )


def calculate_rsi(
    df: pl.LazyFrame, period: int = 14, col_name: str = "close"
) -> pl.LazyFrame:
    """
    Calculate Relative Strength Index (RSI).
    RSI = 100 - (100 / (1 + RS))
    RS = Avg Gain / Avg Loss
    """
    delta = pl.col(col_name).diff()

    # Gain: max(delta, 0), Loss: -min(delta, 0) (so loss is positive)
    up = pl.when(delta > 0).then(delta).otherwise(0)
    down = pl.when(delta < 0).then(-delta).otherwise(0)

    # Wilder's Smoothing usually used for RSI (ewm with com=period-1)
    # pandas_ta uses alpha = 1/period.
    # ewm_mean(span=period) -> alpha = 2/(span+1)
    # We'll use a simple ewm_mean with com=period-1 to match Wilder's method if possible,
    # or just standard ewm_mean for approximation.
    # Polars ewm_mean supports 'com'.

    avg_gain = up.ewm_mean(com=period - 1, adjust=False)
    avg_loss = down.ewm_mean(com=period - 1, adjust=False)

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return df.with_columns(rsi.alias(f"rsi_{period}"))


def calculate_relative_volume(
    df: pl.LazyFrame, period: int = 20, col_name: str = "volume"
) -> pl.LazyFrame:
    """
    Calculate Relative Volume (RVOL).
    RVOL = Volume / Average Volume (SMA of Volume)
    """
    # We calculate the rolling mean of volume first
    avg_vol = pl.col(col_name).rolling_mean(window_size=period)
    
    return df.with_columns([
        avg_vol.alias(f"avg_volume_{period}"),
        (pl.col(col_name) / avg_vol).alias(f"rvol_{period}")
    ])


def calculate_atr(df: pl.LazyFrame, period: int = 14) -> pl.LazyFrame:
    """
    Calculate Average True Range (ATR).
    TR = max(High - Low, |High - Previous Close|, |Low - Previous Close|)
    """
    prev_close = pl.col("close").shift(1)
    
    tr1 = pl.col("high") - pl.col("low")
    tr2 = (pl.col("high") - prev_close).abs()
    tr3 = (pl.col("low") - prev_close).abs()
    
    tr = pl.max_horizontal(tr1, tr2, tr3)
    
    # Wilder's smoothing is standard for ATR, but simple rolling mean is often used too.
    # We'll use simple rolling mean for performance/simplicity in MVP unless precise Wilder is needed.
    # To match standard TA libs better, we can use ewm_mean with com=period-1 (Wilder).
    atr = tr.ewm_mean(com=period - 1, adjust=False)
    
    return df.with_columns(atr.alias(f"atr_{period}"))


def calculate_adr(df: pl.LazyFrame, period: int = 20) -> pl.LazyFrame:
    """
    Calculate Average Daily Range (ADR) as a percentage.
    Daily Range % = (High - Low) / Low * 100
    ADR = Simple Moving Average of Daily Range %
    """
    daily_range_pct = (pl.col("high") - pl.col("low")) / pl.col("low") * 100
    adr = daily_range_pct.rolling_mean(window_size=period)
    
    return df.with_columns(adr.alias(f"adr_{period}"))


def calculate_rolling_extrema(df: pl.LazyFrame, period: int = 252) -> pl.LazyFrame:
    """
    Calculate rolling Min (Low) and Max (High) over a period (e.g. 52 weeks).
    """
    return df.with_columns([
        pl.col("high").rolling_max(window_size=period).alias(f"high_{period}"),
        pl.col("low").rolling_min(window_size=period).alias(f"low_{period}")
    ])


def add_common_indicators(lf: pl.LazyFrame) -> pl.LazyFrame:
    """
    Add a standard suite of indicators: SMA50, SMA200, RSI14.
    """
    lf = calculate_sma(lf, 50)
    lf = calculate_sma(lf, 200)
    lf = calculate_rsi(lf, 14)
    return lf
