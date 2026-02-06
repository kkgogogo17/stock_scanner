# Trading System Task Tracker

Last updated: 2026-02-05

## Usage

- Status values: `todo`, `in_progress`, `blocked`, `done`.
- Keep this file updated as the single execution board for implementation work.

## Phase 1: Daily Backtest Foundation

### A. Backtest Core

- [ ] (`todo`) Create `src/backtest/engine.py` daily event loop (signal at `t`, fill at `t+1`).
- [ ] (`todo`) Define `Bar`/dataset contract with timeframe field (`1d` now, `1h` ready).
- [ ] (`todo`) Make engine config accept timeframe and session calendar abstraction.
- [ ] (`todo`) Create `src/backtest/portfolio.py` cash/positions accounting.
- [ ] (`todo`) Add commission + slippage model in `src/backtest/costs.py`.
- [ ] (`todo`) Add exit logic module: hard stop, trailing stop, time stop.
- [ ] (`todo`) Add performance metrics module: CAGR, max drawdown, win rate, expectancy.
- [ ] (`todo`) Add CLI command `backtest` in `src/cli.py`.

### B. Trend Breakout Strategy v1

- [ ] (`todo`) Create `src/strategies/trend_breakout_v1.py`.
- [ ] (`todo`) Implement trend template filters (`close > sma50 > sma150 > sma200`, `sma200_up`).
- [ ] (`todo`) Implement breakout trigger (`N`-day high configurable).
- [ ] (`todo`) Implement ATR-based initial stop and risk-based sizing.
- [ ] (`todo`) Add strategy config schema and one default YAML in `strategies/`.

### C. Regime Layer v1

- [ ] (`todo`) Create `src/regime/model.py` with SPY 200D and ATR-state logic.
- [ ] (`todo`) Define regime states: `trend_on`, `trend_caution`, `trend_off`.
- [ ] (`todo`) Integrate regime gate into backtest entry permissions and risk scaling.

### D. Signal Delivery v1

- [ ] (`todo`) Create `src/signals/report.py` to produce daily ranked actionable signals.
- [ ] (`todo`) Create `src/signals/telegram.py` adapter interface with dry-run mode.
- [ ] (`todo`) Add CLI command `signal-daily` for report generation and optional send.

### E. Data Quality Guardrails

- [ ] (`todo`) Add data freshness check (exclude stale symbols by default).
- [ ] (`todo`) Add missing/duplicate bar checks for each symbol.
- [ ] (`todo`) Add adjusted-vs-unadjusted policy and make it explicit in configs.
- [ ] (`todo`) Introduce timeframe-aware storage layout (`data/{timeframe}/{symbol}.parquet`).

### F. Testing

- [x] (`done`) Add baseline characterization tests for existing scanner/filter behavior (`tests/test_scanner_engine.py`).
- [ ] (`todo`) Create `tests/test_backtest_engine.py` for no-lookahead and fills.
- [ ] (`todo`) Create `tests/test_costs_and_pnl.py` for commission/slippage accounting.
- [ ] (`todo`) Create `tests/test_exits.py` for stop/trailing/time exits.
- [ ] (`todo`) Create `tests/test_regime_gate.py` for regime behavior.
- [ ] (`todo`) Create one deterministic integration test with known expected equity/trades.
- [ ] (`todo`) Add compatibility tests to run engine on both `1d` and synthetic `1h` fixtures.

## Phase 2: Strategy Mining and Expansion

- [ ] (`todo`) Create feature logging pipeline under `src/research/features.py`.
- [ ] (`todo`) Add experiment runner for parameter sweeps and OOS splits.
- [ ] (`todo`) Add walk-forward evaluation utilities.
- [ ] (`todo`) Add additional trend variants (VCP-like, RS ranking).
- [ ] (`todo`) Start mean reversion research track (separate strategy module).

## Phase 3: Operations and Hardening

- [ ] (`todo`) Add scheduled workflow: sync -> QA -> backtest -> signals.
- [ ] (`todo`) Add run logs and failure alert hooks.
- [ ] (`todo`) Add stale-data and pipeline-health alerts.
- [ ] (`todo`) Add optional IBKR order ticket/export support.

## Current Focus

1. Backtest core skeleton.
2. Trend breakout strategy v1.
3. Regime layer v1.
4. Data quality checks for daily pipeline.
