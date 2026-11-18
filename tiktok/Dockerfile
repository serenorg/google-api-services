# ABOUTME: Builds the gateway-authenticated public TikTok service.
# ABOUTME: Includes shared bounded fetching and residential proxy batching on port 8010.
FROM python:3.12-slim
WORKDIR /app
COPY shared/ /app/shared/
COPY tiktok/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY tiktok/ /app/tiktok/
EXPOSE 8010
CMD ["uvicorn", "tiktok.main:app", "--host", "0.0.0.0", "--port", "8010"]
