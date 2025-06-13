FROM python:3.10

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 安装 tesseract-ocr
RUN apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng && rm -rf /var/lib/apt/lists/*

EXPOSE 9090

CMD ["python", "app/main.py"] 