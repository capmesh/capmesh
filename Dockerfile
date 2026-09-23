FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

RUN pip install --no-cache-dir ".[server]"

ENV CAPMESH_ROOT=/data

EXPOSE 8080

VOLUME ["/data"]

CMD ["capmesh", "server", "start", "--host", "0.0.0.0", "--port", "8080"]
