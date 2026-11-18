# ABOUTME: Packages website contact extraction for Cloud Run on port 8008.
# ABOUTME: Copies the shared gateway, fetch and billing helpers with the service.
FROM python:3.12-slim

WORKDIR /app
COPY web_contacts/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ /app/shared/
COPY web_contacts/ /app/web_contacts/
EXPOSE 8008
CMD ["uvicorn", "web_contacts.main:app", "--host", "0.0.0.0", "--port", "8008"]
