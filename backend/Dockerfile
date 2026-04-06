FROM python:3.12-slim
WORKDIR /app

# System packages for OCR (Tesseract) and PDF rendering (Poppler)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]
