FROM python:3.9

WORKDIR /app

# Install system tools
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages (soundfile is critical!)
RUN pip install --no-cache-dir redis minio demucs soundfile

COPY worker.py .

CMD ["python3", "worker.py"]
