# Implementation Plan: Trend Template & Volatility Indicators

## Overview
This plan outlines the steps to add "Trend Template" (Minervini style) scanning capabilities and Volatility indicators (ATR, ADR) to the Stock Scanner. This will enable users to filter for high-probability setups based on established trading methodologies.

## Requirements
1.  **New Indicators:**
    - Average True Range (ATR)
    - Average Daily Range (ADR)
    - 52-Week High/Low (Rolling Max/Min)
2.  **New Scan Logic:**
    - "Trend Template" filter:
        - Price > SMA50 > SMA150 > SMA200
        - SMA200 trending up
        - Price > 52w Low + 25%
        - Price near 52w High (within 25%)

## Architecture Changes

### 1. `src/indicators/technical.py`
- Add `calculate_atr(df, period=14)`
- Add `calculate_adr(df, period=20)`
- Add `calculate_rolling_extrema(df, period=252)` (for 52w High/Low)

### 2. `src/scanner/engine.py`
- Update `scan()` method to include a `trend_template` boolean flag (or strategy enum).
- Implement the specific filtering logic for the Trend Template using Polars expressions.

### 3. `src/cli.py`
- Add `--trend-template` flag to the `scan` command.
- Add `--min-adr` option to filter by volatility.

## Implementation Steps

### Phase 1: Indicators (Technical Analysis)
1.  **Implement TR & ATR** (`src/indicators/technical.py`)
    - Calculate True Range (TR).
    - Calculate ATR (Rolling mean of TR).
2.  **Implement ADR** (`src/indicators/technical.py`)
    - Calculate Daily Range %: `(High - Low) / Low`.
    - Calculate ADR (Rolling mean).
3.  **Implement Rolling High/Low** (`src/indicators/technical.py`)
    - Use `rolling_max` and `rolling_min` on High and Low columns.

### Phase 2: Scanner Logic
1.  **Update `ScannerEngine.scan`** (`src/scanner/engine.py`)
    - Integrate the new indicators into the lazy frame pipeline.
    - Add the boolean logic for "Trend Template":
      ```python
      # Pseudocode
      (close > sma_50) & (sma_50 > sma_150) & (sma_150 > sma_200) &
      (close > fifty_two_week_low * 1.25) &
      (close > fifty_two_week_high * 0.75)
      ```
    - *Note:* Checking if "SMA200 is trending up" requires comparing current SMA200 vs SMA200 from 20 days ago. This might require an `shift` operation or simpler approximation for the MVP.

### Phase 3: CLI Integration
1.  **Update CLI Scan Command** (`src/cli.py`)
    - Add flags: `--trend-template`, `--min-adr`.
    - Pass these to the engine.

## Testing Strategy
- **Unit Tests:** Verify ATR/ADR calculations against manual examples or known library values (e.g., pandas-ta if available, or manual check).
- **Integration Test:** Run a scan with `--trend-template` on known bullish stocks (e.g., NVDA, META in their uptrends) to ensure they appear.

## Risks & Mitigations
- **Performance:** Calculating rolling windows (252 days) on all stocks might be slow.
  - *Mitigation:* Polars is fast. If needed, pre-filter stocks with very low volume before calculating heavy indicators.
- **Data Quality:** 52-week high requires at least 1 year of data.
  - *Mitigation:* Ensure `sync` fetches enough history. Handle `null`s for recent IPOs gracefully.
