FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    inotify-tools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir watchfiles

EXPOSE 2508

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "2508", "--reload"]
