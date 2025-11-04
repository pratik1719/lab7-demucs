FROM python:3.9-slim

WORKDIR /app

# Install Python libraries
RUN pip install --no-cache-dir flask redis minio

# Copy our code
COPY rest-server.py .

EXPOSE 5000

CMD ["python", "rest-server.py"]
