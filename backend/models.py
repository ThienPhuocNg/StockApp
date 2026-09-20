from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)       # vd: ACB, VNM, FPT
    side = Column(String, nullable=False)                     # "BUY" hoac "SELL"
    quantity = Column(Float, nullable=False)                  # so luong co phieu
    price = Column(Float, nullable=False)                     # gia khop lenh (nghin VND)
    fee = Column(Float, default=0.0)                          # phi giao dich
    trade_date = Column(DateTime, default=datetime.utcnow)    # ngay giao dich
    note = Column(String, nullable=True)
