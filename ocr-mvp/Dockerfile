FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    paddlepaddle==3.2.0 \
    paddleocr==3.7.0

COPY run_ocr.py .

ENTRYPOINT ["python", "run_ocr.py"]
CMD ["/input/sample.png"]