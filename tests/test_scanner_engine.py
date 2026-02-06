from __future__ import annotations

from datetime import date, timedelta

import polars as pl

from src.scanner.engine import ScannerEngine
from src.scanner.filters.common import MinPriceFilter, MinRVolFilter
from src.scanner.filters.gap import GapUpFilter
from src.scanner.filters.trend import TrendTemplateFilter


def _write_symbol_data(
    base_dir,
    symbol: str,
    rows: list[dict],
) -> None:
    df = pl.DataFrame(rows)
    df.write_parquet(base_dir / f"{symbol}.parquet")


def test_scanner_returns_latest_row_per_symbol(tmp_path):
    data_dir = tmp_path / "daily"
    data_dir.mkdir()

    _write_symbol_data(
        data_dir,
        "AAA",
        [
            {
                "date": date(2026, 1, 1),
                "open": 10.0,
                "high": 11.0,
                "low": 9.5,
                "close": 10.5,
                "volume": 1000,
            },
            {
                "date": date(2026, 1, 2),
                "open": 11.0,
                "high": 12.0,
                "low": 10.5,
                "close": 11.5,
                "volume": 1200,
            },
        ],
    )
    _write_symbol_data(
        data_dir,
        "BBB",
        [
            {
                "date": date(2026, 1, 1),
                "open": 20.0,
                "high": 20.5,
                "low": 19.5,
                "close": 20.0,
                "volume": 500,
            },
            {
                "date": date(2026, 1, 3),
                "open": 21.0,
                "high": 22.0,
                "low": 20.5,
                "close": 21.5,
                "volume": 700,
            },
        ],
    )

    result = ScannerEngine(data_dir=data_dir).scan(filters=[])
    by_symbol = {row["symbol"]: row for row in result.iter_rows(named=True)}

    assert set(by_symbol) == {"AAA", "BBB"}
    assert by_symbol["AAA"]["date"] == date(2026, 1, 2)
    assert by_symbol["BBB"]["date"] == date(2026, 1, 3)


def test_min_price_and_gap_filters(tmp_path):
    data_dir = tmp_path / "daily"
    data_dir.mkdir()

    _write_symbol_data(
        data_dir,
        "GAP",
        [
            {
                "date": date(2026, 1, 1),
                "open": 10.0,
                "high": 11.0,
                "low": 9.5,
                "close": 10.5,
                "volume": 1000,
            },
            {
                "date": date(2026, 1, 2),
                "open": 11.6,  # > prev_high(11.0) * 1.05
                "high": 12.2,
                "low": 11.2,
                "close": 12.0,
                "volume": 1800,
            },
        ],
    )
    _write_symbol_data(
        data_dir,
        "NOGAP",
        [
            {
                "date": date(2026, 1, 1),
                "open": 10.0,
                "high": 11.0,
                "low": 9.5,
                "close": 10.5,
                "volume": 1000,
            },
            {
                "date": date(2026, 1, 2),
                "open": 11.2,  # <= prev_high(11.0) * 1.05
                "high": 11.6,
                "low": 10.8,
                "close": 11.1,
                "volume": 1800,
            },
        ],
    )

    filters = [MinPriceFilter(11.5), GapUpFilter(5.0)]
    result = ScannerEngine(data_dir=data_dir).scan(filters=filters)
    symbols = set(result["symbol"].to_list())

    assert symbols == {"GAP"}


def test_rvol_and_trend_template_filters(tmp_path):
    data_dir = tmp_path / "daily"
    data_dir.mkdir()
    start = date(2024, 1, 1)

    trend_rows: list[dict] = []
    flat_rows: list[dict] = []

    for i in range(280):
        d = start + timedelta(days=i)

        trend_close = 50.0 + i * 0.8
        trend_volume = 1_000_000 if i < 279 else 2_000_000
        trend_rows.append(
            {
                "date": d,
                "open": trend_close - 0.5,
                "high": trend_close + 1.0,
                "low": trend_close - 1.0,
                "close": trend_close,
                "volume": trend_volume,
            }
        )

        flat_close = 100.0
        flat_rows.append(
            {
                "date": d,
                "open": flat_close,
                "high": flat_close + 0.5,
                "low": flat_close - 0.5,
                "close": flat_close,
                "volume": 1_000_000,
            }
        )

    _write_symbol_data(data_dir, "TREND", trend_rows)
    _write_symbol_data(data_dir, "FLAT", flat_rows)

    filters = [MinRVolFilter(1.5), TrendTemplateFilter()]
    result = ScannerEngine(data_dir=data_dir).scan(filters=filters)
    symbols = set(result["symbol"].to_list())

    assert symbols == {"TREND"}
