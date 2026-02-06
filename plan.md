# Implementation Plan: Strategy-First Trading System (Daily EOD)

## Why This Plan Exists

The scanner is useful, but the long-term money-maker is validated edge plus disciplined execution.
This plan shifts the project from "scanner MVP" to a strategy-research and decision pipeline that is reliable enough for real capital.

## Context and Constraints (as of 2026-02-05)

- Data provider: Tiingo EOD historical data.
- Broker: IBKR.
- Trading style: Daily timeframe (not intraday), part-time execution.
- Initial execution model: Server sends signals to notification channel (Telegram first), orders are placed manually.
- Strategy priority:
  - First: Trend breakout / trend following.
  - Later: Mean reversion.
- Required capability: Regime filter to reduce/stop trend strategy in unfavorable conditions.

## Current Gaps to Close

1. No backtesting engine exists yet.
2. No data quality/freshness gate in scanner output.
3. No strategy mining framework (feature logging + experiment tracking).
4. No regime model integrated into scanning/backtesting/signal generation.
5. No execution-ready daily signal delivery pipeline.
6. Tests are missing, so edge can be overstated by silent bugs.

## Architecture Direction

Keep one monorepo and separate concerns:

- `src/data`: ingestion, validation, storage interfaces.
- `src/scanner`: candidate generation and ranking.
- `src/backtest`: simulation engine and portfolio accounting.
- `src/strategies`: strategy definitions and parameter sets.
- `src/regime`: market regime calculation and policy gates.
- `src/signals`: daily signal report + notification adapters.
- `src/research`: strategy mining utilities and experiment tracking.

Build all new modules with timeframe abstraction from day one:

- Avoid hardcoding `"daily"` assumptions inside backtest/strategy logic.
- Use a shared bar schema and timeframe metadata (`1d`, `1h`, future `15m`).
- Keep signal timestamp semantics explicit (`signal_time`, `execution_time`).
- Isolate data access behind repository interfaces so source cadence can change without strategy rewrites.

## Phase 1 Plan (Build Now)

### Goal

Ship a reliable daily backtesting foundation and one fully testable trend-breakout strategy pipeline.

### Deliverables

1. Backtest core engine (daily bars, no lookahead).
2. One trend-breakout strategy implemented end-to-end.
3. Regime filter v1 integrated into backtest and signal generation.
4. Daily signal message generator (Telegram adapter interface + dry-run command).
5. Minimum testing baseline for correctness and regression safety.

### Scope Details

#### 1) Backtest Core

- Deterministic daily event model:
  - compute signal on day `t` close;
  - fill at day `t+1` open (or configurable fill rule).
- Engine interface must be timeframe-agnostic:
  - accept bar frequency as config (`1d` now, `1h` later);
  - use session/calendar helpers rather than assuming 1 bar/day;
  - support pluggable fill policy per timeframe.
- Portfolio logic:
  - cash ledger;
  - open positions;
  - max positions;
  - risk per trade sizing.
- Trading costs:
  - fixed commission + bps slippage model.
- Exit framework:
  - hard stop;
  - trailing stop;
  - time-based exit.
- Outputs:
  - trades table;
  - equity curve;
  - drawdown;
  - core metrics (CAGR, max DD, win rate, expectancy).

#### 2) Trend Breakout Strategy v1

- Universe filters:
  - minimum price;
  - minimum liquidity threshold.
- Trend filters:
  - `close > sma50 > sma150 > sma200`;
  - `sma200` trending up.
- Trigger:
  - breakout above `N`-day high (e.g., 20/50 configurable).
- Risk model:
  - initial stop using ATR multiple;
  - position size from per-trade risk budget.

#### 3) Regime Layer v1

- Baseline regime inputs (daily):
  - SPY above/below 200D SMA;
  - SPY volatility state proxy (ATR percentile).
- Policy:
  - `trend_on`: normal risk;
  - `trend_caution`: reduced risk;
  - `trend_off`: no new trend entries.

#### 4) Signal Delivery v1

- Generate daily ranked signal report after EOD sync.
- Message includes:
  - symbol;
  - entry trigger;
  - stop;
  - size;
  - regime state;
  - reason tags.
- Telegram sender interface with dry-run mode.

#### 5) Tests (Must-Have in Phase 1)

- Unit tests:
  - no-lookahead guarantee;
  - fill/commission/slippage math;
  - stop/exit behavior;
  - position sizing invariants.
- Integration tests:
  - one deterministic toy dataset with known expected trades and PnL.
- Forward-compatibility tests:
  - same engine API runs on synthetic `1d` and `1h` fixtures;
  - strategy modules fail fast when required timeframe features are missing.

## Phase 2 Plan (After Phase 1 Stabilizes)

1. Strategy mining framework:
  - feature store per symbol/day;
  - experiment runs with parameter sweeps;
  - out-of-sample and walk-forward validation.
2. Additional trend variants:
  - volatility contraction + breakout;
  - relative strength ranking.
3. Risk overlay expansion:
  - portfolio heat;
  - sector/industry concentration controls.
4. Mean reversion research track (separate pipeline).

## Phase 3 Plan (Operational Hardening)

1. Automation and scheduling:
  - nightly sync -> data QA -> backtest refresh -> signal publish.
2. Observability:
  - run logs;
  - failure alerts;
  - stale data alarms.
3. Execution support:
  - optional IBKR order ticket export or assisted order prep.
4. Research governance:
  - versioned configs;
  - experiment registry;
  - reproducibility checks.

## Definition of Done for Phase 1

Phase 1 is complete only when:

1. A full backtest can run from CLI and produce deterministic metrics.
2. Strategy signals and backtest assumptions are consistent.
3. Regime gating changes position-taking behavior as designed.
4. Core tests pass locally and catch intentional bug injections.
5. Daily signal report can be generated and sent in dry-run mode.
