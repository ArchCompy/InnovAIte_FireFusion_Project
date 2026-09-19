FROM python:3.11-slim

WORKDIR /app

# Build context is backend/ (not this directory) so shared/ is reachable.
# See docs/distributed-tracing.md.

COPY model-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY model-api/. .
COPY shared ./shared

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
