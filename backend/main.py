import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import models
import schemas
import data_fetcher
import predictor
from database import engine, get_db, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="VN Stock Portfolio Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # mo cho demo; khi deploy that co the gioi han lai theo domain
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Giao dich (transactions) ----------

@app.post("/transactions", response_model=schemas.TransactionOut)
def create_transaction(tx: schemas.TransactionCreate, db: Session = Depends(get_db)):
    db_tx = models.Transaction(
        symbol=tx.symbol,
        side=tx.side,
        quantity=tx.quantity,
        price=tx.price,
        fee=tx.fee,
        trade_date=tx.trade_date or datetime.utcnow(),
        note=tx.note,
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx


@app.get("/transactions", response_model=list[schemas.TransactionOut])
def list_transactions(db: Session = Depends(get_db)):
    return db.query(models.Transaction).order_by(models.Transaction.trade_date.desc()).all()


@app.delete("/transactions/{tx_id}")
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = db.query(models.Transaction).filter(models.Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Khong tim thay giao dich")
    db.delete(tx)
    db.commit()
    return {"ok": True}


# ---------- Danh muc (portfolio) ----------

@app.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    txs = db.query(models.Transaction).all()
    holdings: dict[str, dict] = {}

    for tx in txs:
        h = holdings.setdefault(tx.symbol, {"quantity": 0.0, "cost": 0.0})
        if tx.side == "BUY":
            h["quantity"] += tx.quantity
            h["cost"] += tx.quantity * tx.price + tx.fee
        else:  # SELL
            if h["quantity"] > 0:
                avg_cost = h["cost"] / h["quantity"]
                h["cost"] -= avg_cost * tx.quantity
            h["quantity"] -= tx.quantity

    result = []
    for symbol, h in holdings.items():
        if h["quantity"] <= 0.0001:
            continue
        avg_cost = h["cost"] / h["quantity"] if h["quantity"] else 0
        try:
            current_price = data_fetcher.get_latest_price(symbol)
        except Exception:
            current_price = None

        pl = None
        pl_pct = None
        if current_price is not None:
            pl = (current_price - avg_cost) * h["quantity"]
            pl_pct = (current_price / avg_cost - 1) * 100 if avg_cost else None

        result.append({
            "symbol": symbol,
            "quantity": round(h["quantity"], 2),
            "avg_cost": round(avg_cost, 2),
            "current_price": current_price,
            "profit_loss": round(pl, 2) if pl is not None else None,
            "profit_loss_pct": round(pl_pct, 2) if pl_pct is not None else None,
        })

    return {"holdings": result}


# ---------- Du lieu gia & Du doan ----------

@app.get("/price/{symbol}")
def get_price_history(symbol: str, days: int = 180):
    try:
        df = data_fetcher.get_history(symbol, days=days)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    df_tail = df.tail(days)
    return {
        "symbol": symbol.upper(),
        "data": [
            {
                "time": row["time"].strftime("%Y-%m-%d"),
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
            }
            for _, row in df_tail.iterrows()
        ],
    }


@app.get("/predict/{symbol}")
def get_prediction(symbol: str):
    try:
        df = data_fetcher.get_history(symbol, days=500)
        pred = predictor.predict_signal(df)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "symbol": symbol.upper(),
        "signal": pred.signal,
        "probability_up": pred.prob_up,
        "confidence": pred.confidence,
        "reason": pred.reason,
        "indicators": pred.indicators,
        "disclaimer": (
            "Day la du doan thong ke tu mo hinh Machine Learning dua tren du lieu "
            "lich su, khong phai loi khuyen dau tu. Vui long tu nghien cuu them."
        ),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Phuc vu frontend (de deploy thanh 1 service duy nhat) ----------
# Neu co thu muc "frontend" nam ke ben "backend" (nhu cau truc goc), phuc vu no
# tai domain goc, de khi deploy chi can 1 service la truy cap duoc ca web lan API.
_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
