FROM python:3.12-slim

# OpenCV 依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 将模型权重放入此目录（volume 挂载）
RUN mkdir -p /app/weights

COPY . .

# 数据目录（抓拍图片本地缓存，与后端共享或独立）
RUN mkdir -p /data/images

CMD ["python", "-m", "inference.main"]
