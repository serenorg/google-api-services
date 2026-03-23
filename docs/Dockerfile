FROM python:3.12-slim

WORKDIR /app

# Copy shared module
COPY shared/ /app/shared/

# Copy service files
COPY docs/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY docs/ .

EXPOSE 8004

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
