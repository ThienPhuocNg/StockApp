import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Cho phep chi dinh duong dan file DB qua bien moi truong DB_PATH, de khi deploy
# tren cac nen tang co "persistent disk" (vd Render) thi du lieu khong bi mat
# moi lan app khoi dong lai. Mac dinh dung file cung thu muc (chi phu hop chay local).
_DB_PATH = os.environ.get("DB_PATH", "./portfolio.db")
DATABASE_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
