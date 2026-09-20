from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class TransactionCreate(BaseModel):
    symbol: str
    side: str  # BUY / SELL
    quantity: float
    price: float
    fee: float = 0.0
    trade_date: Optional[datetime] = None
    note: Optional[str] = None

    @field_validator("side")
    @classmethod
    def side_must_be_valid(cls, v):
        v = v.upper()
        if v not in ("BUY", "SELL"):
            raise ValueError("side phai la BUY hoac SELL")
        return v

    @field_validator("symbol")
    @classmethod
    def symbol_upper(cls, v):
        return v.upper().strip()


class TransactionOut(TransactionCreate):
    id: int
    trade_date: datetime

    class Config:
        from_attributes = True
