FROM python:3.10-slim

WORKDIR /app

RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

COPY main/rating-service/requirements.txt main/rating-service/requirements.txt
RUN pip install --no-cache-dir -r main/rating-service/requirements.txt

COPY main/shared/ ./main/shared/
COPY main/rating-service/ ./main/rating-service/

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8007/health')" || exit 1

EXPOSE 8007

USER appuser

CMD ["python", "main/rating-service/app.py"]
