import polars as pl

def calculate_sma(df: pl.LazyFrame, period: int, col_name: str = "close") -> pl.LazyFrame:
    """
    Calculate Simple Moving Average (SMA).
    """
    return df.with_columns(
        pl.col(col_name).rolling_mean(window_size=period).alias(f"sma_{period}")
    )

def calculate_ema(df: pl.LazyFrame, period: int, col_name: str = "close") -> pl.LazyFrame:
    """
    Calculate Exponential Moving Average (EMA).
    Polars ewm_mean is available on Expr.
    """
    return df.with_columns(
        pl.col(col_name).ewm_mean(span=period, adjust=False).alias(f"ema_{period}")
    )

def calculate_rsi(df: pl.LazyFrame, period: int = 14, col_name: str = "close") -> pl.LazyFrame:
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

def add_common_indicators(lf: pl.LazyFrame) -> pl.LazyFrame:
    """
    Add a standard suite of indicators: SMA50, SMA200, RSI14.
    """
    lf = calculate_sma(lf, 50)
    lf = calculate_sma(lf, 200)
    lf = calculate_rsi(lf, 14)
    return lf
