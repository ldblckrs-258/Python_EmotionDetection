FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    inotify-tools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install watchfiles for better reload performance
RUN pip install --no-cache-dir watchfiles

# Do not copy application code - it will be mounted as a volume
# This prevents issues with file permissions and improves development experience

# Expose the port the app runs on
EXPOSE 2508

# Use an entrypoint script that can handle file watching
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "2508", "--reload"]
