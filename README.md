# Sổ Lệnh — App theo dõi danh mục & dự đoán mua/bán chứng khoán VN

Full-stack app: **FastAPI (Python) + SQLite** ở backend, **HTML/JS (Chart.js)** ở frontend.

## Tính năng
- Ghi lại từng lệnh **mua/bán** (mã, khối lượng, giá, phí) — lưu trong SQLite.
- Tự tính **danh mục hiện tại**: số lượng đang giữ, giá vốn trung bình, lãi/lỗ.
- Lấy **giá thật** của cổ phiếu HOSE/HNX qua thư viện [`vnstock`](https://github.com/thinh-vu/vnstock) (miễn phí, không cần API key, lấy dữ liệu từ VCI).
- Tính các **chỉ báo kỹ thuật**: SMA10/20/50, RSI14, MACD.
- **Mô hình Machine Learning** (Random Forest) học trên chính lịch sử giá của mã đó để dự đoán xác suất giá tăng trong 5 phiên tới → quy ra tín hiệu **MUA / BÁN / GIỮ**.

## Cài đặt & chạy thử (local)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend chạy tại `http://localhost:8000` (xem docs tự động tại `http://localhost:8000/docs`).

Mở file `frontend/index.html` trực tiếp bằng trình duyệt (hoặc `python3 -m http.server` trong thư mục `frontend`). Dashboard sẽ tự gọi API tại `http://localhost:8000`.

## Cấu trúc project

```
backend/
  main.py          # FastAPI app, các endpoint
  models.py        # Bảng Transaction (SQLAlchemy)
  schemas.py       # Validate dữ liệu vào/ra (Pydantic)
  database.py       # Kết nối SQLite
  data_fetcher.py    # Lấy giá thật qua vnstock, có cache 15 phút
  predictor.py       # Tính chỉ báo kỹ thuật + mô hình Random Forest
  requirements.txt
frontend/
  index.html        # Dashboard (không cần build, mở thẳng bằng trình duyệt)
```

## API chính

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/transactions` | Thêm 1 lệnh mua/bán |
| GET | `/transactions` | Danh sách giao dịch |
| DELETE | `/transactions/{id}` | Xóa 1 giao dịch |
| GET | `/portfolio` | Danh mục hiện tại + lãi/lỗ |
| GET | `/price/{symbol}?days=180` | Lịch sử giá OHLCV |
| GET | `/predict/{symbol}` | Tín hiệu mua/bán + chỉ báo |

## Về phần "real-time" dữ liệu

`vnstock` lấy dữ liệu **cuối ngày** (EOD) từ nguồn công khai của VCI — đây là cách phổ biến nhất để có dữ liệu miễn phí cho HOSE/HNX, nhưng **không phải dữ liệu khớp lệnh theo mili-giây**. Nếu bạn cần giá khớp lệnh thật sự real-time (tick-by-tick) trong phiên, bạn sẽ cần:
- Gói dữ liệu trả phí như **SSI FastConnect Data**, **VNDIRECT DChart API**, hoặc **TCBS/Entrade API** (cần đăng ký tài khoản công ty chứng khoán + API key).
- Kiến trúc dùng WebSocket để đẩy giá theo thời gian thực về frontend thay vì poll theo chu kỳ.

Code hiện tại được viết để dễ dàng thay `data_fetcher.py` bằng một nguồn dữ liệu khác nếu bạn có API key trả phí — chỉ cần giữ nguyên format DataFrame trả về (`time, open, high, low, close, volume`).

## Về mô hình dự đoán

Model hiện dùng là **Random Forest Classifier** của scikit-learn, huấn luyện lại mỗi lần gọi API trên chính lịch sử ~1-2 năm gần nhất của mã đó, với các đặc trưng: RSI, MACD, độ lệch giá so với SMA20/50, momentum, biến động khối lượng. Đây là baseline hợp lý và **chạy nhanh, không cần GPU**.

Nếu muốn nâng cấp lên mô hình phức tạp hơn (LSTM, Transformer, XGBoost với nhiều đặc trưng hơn, hoặc kết hợp dữ liệu tin tức/tâm lý thị trường), kiến trúc hiện tại cho phép thay thế `predictor.py` mà không cần sửa các phần khác.

**⚠️ Lưu ý quan trọng:** Đây là công cụ hỗ trợ tham khảo dựa trên thống kê lịch sử, **không phải lời khuyên đầu tư**. Thị trường chứng khoán có rủi ro; kết quả dự đoán trong quá khứ không đảm bảo hiệu suất tương lai. Bạn nên tự nghiên cứu thêm và cân nhắc kỹ trước khi ra quyết định mua/bán.

## Deploy để truy cập online

App đã được gộp thành **1 service duy nhất**: backend (FastAPI) tự phục vụ luôn frontend, nên chỉ cần deploy 1 nơi là xong (không cần deploy frontend/backend riêng lẻ). Có sẵn `Dockerfile` để deploy ở bất kỳ nền tảng nào hỗ trợ Docker.

### Cách 1 — Render.com (khuyên dùng, miễn phí, không cần thẻ, dễ nhất)
1. Đẩy code này lên 1 repo GitHub (tạo repo mới, `git init`, `git add .`, `git commit`, `git push`).
2. Vào [render.com](https://render.com) → đăng nhập bằng GitHub → **New → Web Service** → chọn repo vừa tạo.
3. Render tự nhận diện `Dockerfile` và file `render.yaml` đã có sẵn trong repo (đã cấu hình sẵn: chạy Docker, gắn ổ đĩa lưu trữ để dữ liệu SQLite không mất khi restart).
4. Bấm **Deploy**. Sau ~2–3 phút, Render cho bạn 1 link dạng `https://ten-app.onrender.com` — vào link đó là dùng được app.

*Lưu ý gói free của Render: server sẽ "ngủ" sau ~15 phút không ai truy cập, lần truy cập tiếp theo sẽ mất khoảng 30–60 giây để "thức dậy".*

### Cách 2 — Google Cloud Run (vì bạn có nhắc tới Google)
Cần cài [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) và có project GCP (có gói miễn phí).

```bash
gcloud auth login
gcloud config set project TEN-PROJECT-CUA-BAN

# Build va deploy thang tu source code (Cloud Run tu build Docker image)
gcloud run deploy so-lenh-app --source . --region asia-southeast1 --allow-unauthenticated
```
Sau khi chạy xong, Google trả về 1 URL dạng `https://so-lenh-app-xxxx.a.run.app`. Lưu ý: ổ đĩa của Cloud Run là **tạm thời** (mất dữ liệu SQLite mỗi lần deploy lại) — nếu dùng lâu dài nên đổi sang Cloud SQL (PostgreSQL) thay vì SQLite.

### Cách 3 — Railway / Fly.io / VPS bất kỳ
Vì đã có `Dockerfile`, bạn có thể `docker build -t so-lenh .` rồi chạy trên bất kỳ nơi nào hỗ trợ Docker, hoặc kết nối trực tiếp repo GitHub với Railway/Fly.io (cả hai đều tự nhận Dockerfile).

### Ghi chú chung khi deploy thật
- Biến môi trường `DB_PATH` cho phép chỉ định nơi lưu file SQLite (vd trên ổ đĩa bền vững) — mặc định là `./portfolio.db` nếu không set.
- Nếu nhiều người cùng dùng chung 1 app, nên đổi SQLite → PostgreSQL và thêm đăng nhập/phân quyền theo user (hiện tại **chưa có xác thực**, ai có link cũng xem/sửa được danh mục).
- `vnstock` gần đây bắt đầu khuyến khích đăng ký API key miễn phí tại vnstocks.com để ổn định hơn khi gọi nhiều — không bắt buộc để chạy app này nhưng nên biết nếu gặp lỗi giới hạn truy cập (rate limit).
