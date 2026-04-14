# Build
FROM python:3.14-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv pip install --system .

# Runtime
FROM python:3.14-slim

WORKDIR /app

COPY --from=builder /usr/local /usr/local

COPY . .

RUN addgroup --system apigroup && \
    adduser --system --ingroup apigroup apiuser && \
    mkdir -p /app/logs && \
    chown -R apiuser:apigroup /app

USER apiuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]