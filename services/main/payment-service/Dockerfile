FROM python:3.10-slim

WORKDIR /app

RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

COPY main/payment-service/requirements.txt main/payment-service/requirements.txt
RUN pip install --no-cache-dir -r main/payment-service/requirements.txt

COPY main/shared/ ./main/shared/
COPY main/payment-service/ ./main/payment-service/

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8004/health')" || exit 1

EXPOSE 8004

USER appuser

CMD ["python", "main/payment-service/app.py"]
