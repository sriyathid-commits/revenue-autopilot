FROM python:3.12-slim
WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend ./backend
COPY simulator ./simulator

# Create the data directory — on Render this is replaced by the disk mount.
# Locally it holds the SQLite file.
RUN mkdir -p /app/data

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
