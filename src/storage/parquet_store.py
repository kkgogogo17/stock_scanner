import polars as pl
from pathlib import Path
from src.config import DAILY_DATA_DIR

class ParquetStore:
    def __init__(self, data_dir: Path = DAILY_DATA_DIR):
        self.data_dir = data_dir

    def get_file_path(self, symbol: str) -> Path:
        return self.data_dir / f"{symbol.upper()}.parquet"

    def save_ticker_data(self, symbol: str, df: pl.DataFrame):
        """
        Save dataframe to parquet.
        If file exists, we could implement merge logic, but for MVP we overwrite 
        or we assume the fetcher got everything we needed.
        """
        file_path = self.get_file_path(symbol)
        df.write_parquet(file_path)

    def load_ticker_data(self, symbol: str) -> pl.DataFrame:
        """
        Load dataframe from parquet.
        """
        file_path = self.get_file_path(symbol)
        if not file_path.exists():
            raise FileNotFoundError(f"Data for {symbol} not found.")
        
        return pl.read_parquet(file_path)

    def exists(self, symbol: str) -> bool:
        return self.get_file_path(symbol).exists()
    
    def list_existing_tickers(self) -> list[str]:
        return [f.stem for f in self.data_dir.glob("*.parquet")]
