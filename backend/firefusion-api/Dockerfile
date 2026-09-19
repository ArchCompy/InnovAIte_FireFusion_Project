FROM python:3.14

WORKDIR /code

# Build context is backend/ (not this directory) so shared/ is reachable.
# See docs/distributed-tracing.md.

# this contains all the dependencies required for the application
COPY ./firefusion-api/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./firefusion-api/app /code/app
COPY ./shared /code/shared

CMD ["fastapi", "run", "app/main.py", "--port", "8080"]
