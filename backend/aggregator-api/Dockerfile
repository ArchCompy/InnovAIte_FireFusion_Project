FROM python:3.14-slim

WORKDIR /code

# Install Python dependencies before copying application code
# to improve Docker layer caching.
COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Create a dedicated non-root user for the application.
RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY ./app /code/app

# Ensure the application files are owned by the non-root user.
RUN chown -R appuser:appuser /code

USER appuser

EXPOSE 8080

CMD ["fastapi", "run", "app/main.py", "--port", "8080"]
