FROM python:3.12-slim

WORKDIR /app

# Copy shared module
COPY shared/ /app/shared/

# Copy service files
COPY contacts/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY contacts/ .

EXPOSE 8006

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8006"]
