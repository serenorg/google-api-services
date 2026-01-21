# Google API Services

REST API wrappers for Google services, designed for Seren Publisher integration.

## Services

| Service | Port | Google API |
|---------|------|------------|
| **Gmail** | 8001 | `https://gmail.googleapis.com/gmail/v1` |
| **Calendar** | 8002 | `https://www.googleapis.com/calendar/v3` |

## Architecture

```
Agent → Seren Gateway → Publisher → This Service → Google API
                            ↓
                  Token Exchange (OAuth tokens from SerenDB)
```

Each service:
- Receives requests with user's Google OAuth access token (via `Authorization: Bearer`)
- Proxies to Google's REST API
- Returns Google's response

## Local Development

```bash
# Install dependencies
cd gmail && pip install -r requirements.txt
cd calendar && pip install -r requirements.txt

# Run services
cd gmail && uvicorn main:app --port 8001 --reload
cd calendar && uvicorn main:app --port 8002 --reload
```

## Docker

```bash
# Build and run both services
docker-compose up --build

# Or individually
docker build -t seren-gmail ./gmail
docker build -t seren-calendar ./calendar
```

## Environment Variables

```bash
# Optional - for local testing with service account
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# For production, tokens come via Authorization header from Seren Gateway
```

## Deployment

Deploy to Google Cloud Run:

```bash
# Gmail service
gcloud run deploy seren-gmail \
  --source ./gmail \
  --region us-central1 \
  --allow-unauthenticated

# Calendar service
gcloud run deploy seren-calendar \
  --source ./calendar \
  --region us-central1 \
  --allow-unauthenticated
```

## API Reference

### Gmail Service

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/messages` | List messages |
| GET | `/messages/{id}` | Get message |
| POST | `/messages/send` | Send message |
| GET | `/labels` | List labels |
| GET | `/threads` | List threads |
| GET | `/threads/{id}` | Get thread |

### Calendar Service

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/calendars` | List calendars |
| GET | `/events` | List events |
| GET | `/events/{id}` | Get event |
| POST | `/events` | Create event |
| PUT | `/events/{id}` | Update event |
| DELETE | `/events/{id}` | Delete event |
| POST | `/freebusy` | Query free/busy |
