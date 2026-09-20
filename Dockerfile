# Dong goi ca backend (FastAPI) va frontend (file tinh) thanh 1 image duy nhat.
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY frontend ./frontend

WORKDIR /app/backend

# Cac nen tang deploy (Render, Cloud Run, Railway...) thuong truyen PORT qua bien moi truong.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
