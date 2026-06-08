FROM python:3.10-slim

# 安裝基本套件以及 Google Chrome 穩定版與其依賴庫
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    ca-certificates \
    && curl -fsSL https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 安裝 Python 依賴庫
RUN pip install --no-cache-dir selenium undetected-chromedriver beautifulsoup4

# 複製搶票腳本
COPY automate.py /app/

# 設定環境變數讓 Python 程式知道在 Docker 內執行，且不緩衝輸出日誌
ENV IN_DOCKER=true
ENV PYTHONUNBUFFERED=1

# 啟動命令
CMD ["python", "automate.py"]
