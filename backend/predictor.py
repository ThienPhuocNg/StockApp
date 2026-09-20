"""
Sinh tin hieu MUA / BAN / GIU dua tren:
  1. Cac chi bao ky thuat (SMA, RSI, MACD, bien dong khoi luong) lam dac trung (features)
  2. Mo hinh Random Forest Classifier hoc tren chinh lich su gia cua ma co phieu do,
     du doan xac suat gia se TANG trong N ngay giao dich toi.

LUU Y QUAN TRONG:
  - Day la mo hinh thong ke don gian, HOAN TOAN khong phai loi khuyen dau tu.
  - Thi truong chung khoan co rui ro; ket qua qua khu khong dam bao ket qua tuong lai.
  - Nguoi dung nen tu danh gia va chiu trach nhiem voi quyet dinh dau tu cua minh.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

HORIZON_DAYS = 5       # du doan xu huong trong 5 phien toi
UP_THRESHOLD = 0.015   # coi la "tang" neu gia tang > 1.5% trong horizon


@dataclass
class Prediction:
    signal: str          # "BUY" | "SELL" | "HOLD"
    prob_up: float        # xac suat mo hinh du doan gia se tang
    confidence: str        # "thap" | "trung binh" | "cao"
    reason: str
    indicators: dict


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["sma10"] = out["close"].rolling(10).mean()
    out["sma20"] = out["close"].rolling(20).mean()
    out["sma50"] = out["close"].rolling(50).mean()
    out["rsi14"] = _rsi(out["close"], 14)

    ema12 = out["close"].ewm(span=12, adjust=False).mean()
    ema26 = out["close"].ewm(span=26, adjust=False).mean()
    out["macd"] = ema12 - ema26
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["macd_hist"] = out["macd"] - out["macd_signal"]

    out["price_vs_sma20"] = out["close"] / out["sma20"] - 1
    out["price_vs_sma50"] = out["close"] / out["sma50"] - 1
    out["momentum_5d"] = out["close"].pct_change(5)
    out["vol_change_5d"] = out["volume"].pct_change(5)
    return out


FEATURE_COLS = [
    "rsi14", "macd", "macd_hist",
    "price_vs_sma20", "price_vs_sma50",
    "momentum_5d", "vol_change_5d",
]


def predict_signal(df: pd.DataFrame) -> Prediction:
    feat_df = build_features(df)

    # nhan (label): gia dong sau HORIZON_DAYS phien co tang > UP_THRESHOLD khong
    feat_df["future_return"] = (
        feat_df["close"].shift(-HORIZON_DAYS) / feat_df["close"] - 1
    )
    feat_df["label"] = (feat_df["future_return"] > UP_THRESHOLD).astype(int)

    train_df = feat_df.dropna(subset=FEATURE_COLS + ["label"])

    if len(train_df) < 60:
        raise RuntimeError(
            "Khong du du lieu lich su (can toi thieu ~60 phien) de huan luyen mo hinh."
        )

    X_train = train_df[FEATURE_COLS].iloc[:-HORIZON_DAYS] if len(train_df) > HORIZON_DAYS else train_df[FEATURE_COLS]
    y_train = train_df["label"].iloc[:-HORIZON_DAYS] if len(train_df) > HORIZON_DAYS else train_df["label"]

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=5,
        min_samples_leaf=5,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    latest_row = feat_df.dropna(subset=FEATURE_COLS).iloc[[-1]]
    prob_up = float(model.predict_proba(latest_row[FEATURE_COLS])[0][1])

    if prob_up >= 0.62:
        signal, confidence = "BUY", "cao" if prob_up >= 0.72 else "trung binh"
    elif prob_up <= 0.38:
        signal, confidence = "SELL", "cao" if prob_up <= 0.28 else "trung binh"
    else:
        signal, confidence = "HOLD", "thap"

    last = feat_df.iloc[-1]
    reason_bits = []
    if last["rsi14"] > 70:
        reason_bits.append("RSI cho thay vung qua mua")
    elif last["rsi14"] < 30:
        reason_bits.append("RSI cho thay vung qua ban")
    if last["macd_hist"] > 0:
        reason_bits.append("MACD dang cat len (tin hieu tich cuc ngan han)")
    else:
        reason_bits.append("MACD dang cat xuong (tin hieu tieu cuc ngan han)")
    if last["price_vs_sma20"] > 0:
        reason_bits.append("gia dang tren SMA20")
    else:
        reason_bits.append("gia dang duoi SMA20")

    return Prediction(
        signal=signal,
        prob_up=round(prob_up, 4),
        confidence=confidence,
        reason="; ".join(reason_bits),
        indicators={
            "rsi14": round(float(last["rsi14"]), 2),
            "macd_hist": round(float(last["macd_hist"]), 4),
            "sma20": round(float(last["sma20"]), 2) if not pd.isna(last["sma20"]) else None,
            "sma50": round(float(last["sma50"]), 2) if not pd.isna(last["sma50"]) else None,
            "close": round(float(last["close"]), 2),
        },
    )
