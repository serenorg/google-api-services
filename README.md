# Google API Services for SerenAI Publishers

REST API wrappers for Google services, designed for Seren Publisher integration.

## Services

| Service | Port | Google API | Publisher Slug |
|---------|------|------------|----------------|
| **Gmail** | 8001 | `https://gmail.googleapis.com/gmail/v1` | `gmail` |
| **Calendar** | 8002 | `https://www.googleapis.com/calendar/v3` | `google-calendar` |

## Architecture

```
User/Agent → Seren Gateway → Publisher → This Service → Google API
                  │                           │
                  └── Token Exchange ─────────┘
                      (Seren API key → Google access token)
```

### Authentication Flow

1. **First-time authorization**: User visits `/auth/google` to authorize Google access
2. **Token storage**: Refresh token stored (keyed by Seren user)
3. **API calls**: Seren Gateway exchanges API key for Google access token via `/token/exchange`
4. **Token refresh**: Access tokens refreshed automatically when expired

## Endpoints

### OAuth Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/google` | Initiate Google OAuth flow |
| GET | `/auth/google/callback` | OAuth callback, stores refresh token |
| POST | `/token/exchange` | Exchange Seren API key for Google access token |

### Gmail API (`/gmail`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/messages` | List messages (query params: `q`, `maxResults`, `pageToken`) |
| GET | `/messages/{id}` | Get message by ID |
| POST | `/messages/send` | Send email |
| DELETE | `/messages/{id}` | Delete message |
| POST | `/messages/{id}/trash` | Move to trash |
| POST | `/messages/{id}/modify` | Add/remove labels |
| GET | `/labels` | List labels |
| GET | `/threads` | List threads |
| GET | `/threads/{id}` | Get thread with messages |
| GET | `/drafts` | List drafts |
| POST | `/drafts` | Create draft |

### Calendar API (`/calendar`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/calendars` | List calendars |
| GET | `/calendars/{id}` | Get calendar |
| GET | `/events` | List events (query params: `timeMin`, `timeMax`, `q`) |
| GET | `/events/{id}` | Get event |
| POST | `/events` | Create event |
| PUT | `/events/{id}` | Update event |
| PATCH | `/events/{id}` | Partial update event |
| DELETE | `/events/{id}` | Delete event |
| POST | `/quickAdd` | Create event from natural language |
| POST | `/freebusy` | Query free/busy times |
| GET | `/colors` | Get calendar colors |

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
# Required for OAuth flow
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://google-api.serendb.com/auth/google/callback

# Database for token storage
DATABASE_URL=postgresql://user:pass@host:5432/db

# Encryption key for refresh tokens
TOKEN_ENCRYPTION_KEY=your-32-byte-key

# Optional - for local testing
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
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

## Testing with Seren MCP

```bash
# Check publisher health
seren mcp call execute_paid_api --publisher gmail --method GET --path /health

# List messages (requires OAuth authorization first)
seren mcp call execute_paid_api --publisher gmail --method GET --path /messages
```

## OAuth Scopes

**Gmail:**

- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.send`
- `https://www.googleapis.com/auth/gmail.modify`

**Calendar:**

- `https://www.googleapis.com/auth/calendar`
- `https://www.googleapis.com/auth/calendar.events`

## Related

- Seren Publishers: `gmail`, `google-calendar`
- Backend API: [https://docs.serendb.com](https://docs.serendb.com)

## License

MIT License - see [LICENSE](LICENSE) for details.
