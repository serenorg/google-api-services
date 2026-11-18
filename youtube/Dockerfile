# ABOUTME: Builds the standalone YouTube publisher container.
# ABOUTME: Runs the package and shared gateway helpers on port 8007.
FROM python:3.12-slim

WORKDIR /app

COPY youtube/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY youtube/ /app/youtube/

EXPOSE 8007

CMD ["uvicorn", "youtube.main:app", "--host", "0.0.0.0", "--port", "8007"]
