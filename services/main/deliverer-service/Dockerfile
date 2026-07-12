FROM python:3.10-slim

WORKDIR /app

COPY main/deliverer-service/requirements.txt main/deliverer-service/requirements.txt
RUN pip install --no-cache-dir -r main/deliverer-service/requirements.txt

COPY main/shared/ ./main/shared/
COPY main/deliverer-service/ ./main/deliverer-service/

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8009/health')" || exit 1

EXPOSE 8009

CMD ["python", "main/deliverer-service/app.py"]
