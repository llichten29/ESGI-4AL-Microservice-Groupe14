FROM python:3.10-slim

WORKDIR /app

RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

COPY main/delivery-service/requirements.txt main/delivery-service/requirements.txt
RUN pip install --no-cache-dir -r main/delivery-service/requirements.txt

COPY main/shared/ ./main/shared/
COPY main/delivery-service/ ./main/delivery-service/

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8005/health')" || exit 1

EXPOSE 8005

USER appuser

CMD ["python", "main/delivery-service/app.py"]
