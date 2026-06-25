FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y tesseract-ocr poppler-utils && rm -rf /var/lib/apt/lists/*
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt
COPY hf_cache/ /root/.cache/huggingface/hub/

COPY . .

CMD ["python", "worker.py"]