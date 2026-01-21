# CLAUDE.md

## Project Overview

**google-api-services** contains REST API wrappers for Google services, designed for Seren Publisher integration.

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

Each service receives user's Google OAuth access token via `Authorization: Bearer` header and proxies requests to Google's REST API.

## Development Commands

```bash
# Gmail service
cd gmail && pip install -r requirements.txt
uvicorn main:app --port 8001 --reload

# Calendar service
cd calendar && pip install -r requirements.txt
uvicorn main:app --port 8002 --reload

# Docker (both services)
docker-compose up --build
```

## Deployment

```bash
# Gmail
gcloud run deploy seren-gmail --source ./gmail --region us-central1

# Calendar
gcloud run deploy seren-calendar --source ./calendar --region us-central1
```

## Testing

Test with a valid Google OAuth access token:

```bash
# Health check
curl http://localhost:8001/health

# List messages (requires token)
curl -H "Authorization: Bearer <ACCESS_TOKEN>" http://localhost:8001/messages

# List calendars
curl -H "Authorization: Bearer <ACCESS_TOKEN>" http://localhost:8002/calendars
```

## Related

- Seren Publishers: `GMail`, `Google Calendar`
- Design doc: `seren-store/docs/Seren Agents/20260119_Ishan_seren_daily_task_agent.md`
