# Task 2 - Containerize the data processing application
# (python:3.9-slim from the example is end-of-life; 3.11-slim is the supported equivalent)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

WORKDIR /app

# Install dependencies first so Docker caches this layer between code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["python", "data_analysis.py"]
