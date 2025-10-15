FROM python:3.11-alpine

WORKDIR /app

RUN addgroup -S apigroup && adduser -S apiuser -G apigroup

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./ /app

RUN mkdir -p /app/logs && \
    chown -R apiuser:apigroup /app/logs

RUN chown -R apiuser:apigroup /app

USER apiuser

CMD ["uvicorn", "main:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "80"]