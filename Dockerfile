FROM python:3.12-slim
WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend ./backend
COPY simulator ./simulator

# Create the data directory — on Render this path is used for SQLite
RUN mkdir -p /app/data

ENV PYTHONPATH=/app
# Default port — Render overrides this with its own PORT env var
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
