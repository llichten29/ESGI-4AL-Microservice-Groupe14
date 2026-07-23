FROM python:3.10-slim

WORKDIR /app

RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

COPY main/catalog-service/requirements.txt main/catalog-service/requirements.txt
RUN pip install --no-cache-dir -r main/catalog-service/requirements.txt

COPY main/shared/ ./main/shared/
COPY ressources/endpoints/ ./ressources/endpoints/
COPY main/catalog-service/ ./main/catalog-service/

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8003/health')" || exit 1

EXPOSE 8003

USER appuser

CMD ["python", "main/catalog-service/app.py"]
