import requests
import polars as pl
from datetime import datetime, timedelta
from typing import Optional
from src.config import TIINGO_API_KEY


class TiingoClient:
    BASE_URL = "https://api.tiingo.com/tiingo/daily"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or TIINGO_API_KEY
        if not self.api_key:
            raise ValueError("TIINGO_API_KEY is not set.")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_key}",
        }

    def fetch_daily_history(
        self, symbol: str, start_date: str = "1970-1-1"
    ) -> Optional[pl.DataFrame]:
        """
        Fetch historical daily data for a symbol using CSV format for bandwidth efficiency.
        Defaults to 1970-01-01 to capture full history for most stocks.
        """
        url = f"{self.BASE_URL}/{symbol}/prices"
        params = {
            "startDate": start_date,
            "resampleFreq": "daily",
            "format": "csv",  # Request CSV format
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            # Tiingo returns empty CSV if no data (just headers sometimes, or empty text)
            if not response.text or len(response.text.strip()) == 0:
                return None

            # Parse CSV directly into Polars
            # We use io.BytesIO because read_csv expects bytes or file-like
            import io

            data = io.BytesIO(response.content)

            df = pl.read_csv(data)

            # Ensure date column is properly typed
            if "date" in df.columns:
                df = df.with_columns(
                    pl.col("date").str.strptime(pl.Date, format="%Y-%m-%d")
                )

            return df

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error processing {symbol}: {e}")
            return None
