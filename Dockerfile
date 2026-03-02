# 使用官方 Python 輕量版
FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 複製依賴清單並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製其餘程式碼
COPY . .

# 暴露 FastAPI 預設 Port
EXPOSE 8000

# 啟動指令 (使用 uvicorn)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
