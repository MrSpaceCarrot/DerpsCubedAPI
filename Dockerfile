# Build
FROM python:3.14-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

ENV UV_SYSTEM_PYTHON=1

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

# Runtime
FROM python:3.14-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.14 /usr/local/lib/python3.14
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN addgroup --system apigroup && adduser --system --ingroup apigroup apiuser && \
    mkdir -p /app/logs && \
    chown -R apiuser:apigroup /app

USER apiuser

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]