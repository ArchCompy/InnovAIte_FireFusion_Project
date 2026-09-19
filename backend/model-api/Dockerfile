FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Create a dedicated non-root user for the application.
RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY . .

# Ensure the application files are owned by the non-root user.
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
