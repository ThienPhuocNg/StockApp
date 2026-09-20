"""
Lay du lieu gia co phieu VN that (HOSE/HNX/UPCOM) thong qua thu vien vnstock.
vnstock lay du lieu tu cac nguon cong khai (VCI, TCBS...) - mien phi, khong can API key.
Cai dat: pip install vnstock
"""

from datetime import datetime, timedelta
from functools import lru_cache
import time

import pandas as pd
from vnstock.api.quote import Quote  # API moi cua vnstock (thay cho Vnstock().stock(...) da deprecated)

# cache don gian trong bo nho: {symbol: (timestamp, dataframe)}
_CACHE: dict[str, tuple[float, pd.DataFrame]] = {}
_CACHE_TTL_SECONDS = 15 * 60  # 15 phut, tranh goi lien tuc len nguon du lieu


def get_history(symbol: str, days: int = 365, source: str = "VCI") -> pd.DataFrame:
    """
    Tra ve DataFrame lich su gia OHLCV cho `symbol` trong `days` ngay gan nhat.
    Cot: time, open, high, low, close, volume
    """
    symbol = symbol.upper().strip()
    now = time.time()

    cached = _CACHE.get(symbol)
    if cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    end = datetime.now()
    start = end - timedelta(days=days + 30)  # lay du them de tinh chi bao (MA50...)

    try:
        quote = Quote(symbol=symbol, source=source)
        df = quote.history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1D",
        )
    except Exception as e:
        raise RuntimeError(
            f"Khong lay duoc du lieu cho ma {symbol} tu nguon {source}: {e}"
        )

    if df is None or df.empty:
        raise RuntimeError(f"Khong co du lieu cho ma {symbol}")

    df = df.rename(columns=str.lower)
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)

    _CACHE[symbol] = (now, df)
    return df


def get_latest_price(symbol: str) -> float:
    """Gia dong cua gan nhat cua ma chung khoan (nghin VND)."""
    df = get_history(symbol, days=10)
    return float(df.iloc[-1]["close"])
