# Trading Methodologies & Scans

This document outlines 3 popular trading methodologies suitable for the Stock Scanner, along with the indicators and scans required to implement them.

## 1. Momentum / Breakout (Trend Continuation)
**Core Concept:** Identify strong stocks that are consolidating and likely to resume their upward trend. This style, popularized by Mark Minervini (SEPA) and William O'Neil (CANSLIM), focuses on buying high-quality stocks as they emerge from low-volatility bases.

**Key Indicators:**
- **Price vs SMAs:** Price > SMA50 > SMA150 > SMA200 (Trend Template).
- **Relative Strength:** Stock is outperforming the market (needs Index data or proxy).
- **Volatility Contraction:** Volatility (ATR) decreases as the stock consolidates (VCP).
- **Volume:** Low volume during consolidation, high volume on breakout (RVOL).

**Proposed Scans:**
- **"Trend Template" (Minervini):**
  - Price > SMA50 > SMA150 > SMA200
  - Price > 52-week Low + 25%
  - Price > 52-week High - 25% (near highs)
  - SMA200 trending up for > 1 month
- **"Consolidation Breakout":**
  - Meets "Trend Template" criteria
  - Price within 5% of 20-day High
  - 5-Day ATR < 20-Day ATR (Volatility Contracting)
  - Volume < 50-day average volume (Drying up before the move)

## 2. Mean Reversion (Overbought/Oversold)
**Core Concept:** Prices tend to revert to their mean over time. This strategy looks for stocks that have moved too far, too fast, in either direction.

**Key Indicators:**
- **RSI (Relative Strength Index):** Measures speed and change of price movements.
- **Bollinger Bands:** Measures volatility and potential overextension (Price touching bands).
- **Distance from SMA:** % deviation from SMA50 or SMA20.

**Proposed Scans:**
- **"RSI Oversold in Uptrend":**
  - Long-term Trend is UP (Price > SMA200)
  - Short-term dip: RSI(14) < 30 OR RSI(2) < 10
- **"Bollinger Band Snapback":**
  - Price closed below Lower Bollinger Band (20, 2)
  - RSI < 30 (Confirmation)

## 3. Volatility Expansion (Range Expansion)
**Core Concept:** Periods of low volatility are often followed by periods of high volatility (expansion). Capturing the start of this expansion can lead to significant moves.

**Key Indicators:**
- **ATR (Average True Range):** Measures average volatility.
- **ADR (Average Daily Range):** % move per day on average.
- **NR7 (Narrowest Range in 7 Days):** A classic volatility contraction pattern.
- **Inside Day:** Today's High < Yesterday's High AND Today's Low > Yesterday's Low.

**Proposed Scans:**
- **"Vol. Squeeze / Expansion Ready":**
  - NR7 or Inside Day pattern detected
  - ADR(20) > 3% (Ensure the stock is capable of moving)
  - Volume declining over last 3 days
