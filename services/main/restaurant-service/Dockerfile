FROM python:3.10-slim

WORKDIR /app

COPY main/restaurant-service/requirements.txt main/restaurant-service/requirements.txt
RUN pip install --no-cache-dir -r main/restaurant-service/requirements.txt

COPY main/shared/ ./main/shared/
COPY main/restaurant-service/ ./main/restaurant-service/

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8002/health')" || exit 1

EXPOSE 8002

CMD ["python", "main/restaurant-service/app.py"]
