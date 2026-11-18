# ABOUTME: Builds the gateway-authenticated public Instagram service.
# ABOUTME: Includes shared bounded fetching and residential proxy batching on port 8011.
FROM python:3.12-slim
WORKDIR /app
COPY shared/ /app/shared/
COPY instagram/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY instagram/ /app/instagram/
EXPOSE 8011
CMD ["uvicorn", "instagram.main:app", "--host", "0.0.0.0", "--port", "8011"]
