# ABOUTME: FastAPI application for Gmail API service.
# ABOUTME: Exposes REST endpoints that proxy to Google Gmail API.

import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
import httpx

sys.path.insert(0, "..")
from shared.auth import get_token_from_header
from shared.config import get_settings

from client import GmailClient
from models import SendMessageRequest

# Configure logging
settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Gmail API service starting...")
    yield
    logger.info("Gmail API service shutting down...")


app = FastAPI(
    title="Gmail API Service",
    description="REST API wrapper for Google Gmail API",
    version="1.0.0",
    lifespan=lifespan,
)


def get_gmail_client(token: str = Depends(get_token_from_header)) -> GmailClient:
    """Dependency to get Gmail client with user's token."""
    return GmailClient(access_token=token)


def _query_value(request: Request, *names: str) -> Optional[str]:
    """Return the first present query parameter value from a list of aliases."""
    for name in names:
        value = request.query_params.get(name)
        if value is not None:
            return value
    return None


def _query_values(request: Request, *names: str) -> Optional[List[str]]:
    """Return the first non-empty query parameter list from a list of aliases."""
    for name in names:
        values = request.query_params.getlist(name)
        if values:
            return values
    return None


def _query_int(request: Request, default: int, minimum: int, maximum: int, *names: str) -> int:
    """Parse and range-check an integer query parameter from known aliases."""
    value = _query_value(request, *names)
    if value is None:
        return default

    try:
        parsed = int(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid integer for {'/'.join(names)}") from exc

    if parsed < minimum or parsed > maximum:
        raise HTTPException(
            status_code=422,
            detail=f"Query parameter {'/'.join(names)} must be between {minimum} and {maximum}",
        )
    return parsed


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "gmail"}


# --- Messages ---

@app.get("/messages")
async def list_messages(
    request: Request,
    max_results: int = Query(10, ge=1, le=500, alias="maxResults"),
    page_token: Optional[str] = Query(None, alias="pageToken"),
    q: Optional[str] = Query(None, description="Gmail search query"),
    label_ids: Optional[List[str]] = Query(None, alias="labelIds"),
    client: GmailClient = Depends(get_gmail_client),
):
    """List messages in user's mailbox."""
    try:
        max_results = _query_int(request, max_results, 1, 500, "maxResults", "max_results")
        page_token = _query_value(request, "pageToken", "page_token") or page_token
        q = _query_value(request, "q") or q
        label_ids = _query_values(request, "labelIds", "label_ids") or label_ids

        return await client.list_messages(
            max_results=max_results,
            page_token=page_token,
            q=q,
            label_ids=label_ids,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.get("/messages/{message_id}")
async def get_message(
    message_id: str,
    format: str = Query("full", enum=["minimal", "full", "raw", "metadata"]),
    client: GmailClient = Depends(get_gmail_client),
):
    """Get a specific message by ID."""
    try:
        return await client.get_message(message_id=message_id, format=format)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/messages/send")
async def send_message(
    request: SendMessageRequest,
    client: GmailClient = Depends(get_gmail_client),
):
    """Send a message."""
    try:
        return await client.send_message(
            raw=request.raw,
            thread_id=request.thread_id,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    client: GmailClient = Depends(get_gmail_client),
):
    """Delete a message permanently."""
    try:
        await client.delete_message(message_id=message_id)
        return {"status": "deleted", "message_id": message_id}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/messages/{message_id}/trash")
async def trash_message(
    message_id: str,
    client: GmailClient = Depends(get_gmail_client),
):
    """Move a message to trash."""
    try:
        return await client.trash_message(message_id=message_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/messages/{message_id}/modify")
async def modify_message(
    message_id: str,
    add_label_ids: Optional[List[str]] = Query(None),
    remove_label_ids: Optional[List[str]] = Query(None),
    client: GmailClient = Depends(get_gmail_client),
):
    """Modify message labels."""
    try:
        return await client.modify_message(
            message_id=message_id,
            add_label_ids=add_label_ids,
            remove_label_ids=remove_label_ids,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


# --- Labels ---

@app.get("/labels")
async def list_labels(client: GmailClient = Depends(get_gmail_client)):
    """List all labels."""
    try:
        return await client.list_labels()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.get("/labels/{label_id}")
async def get_label(
    label_id: str,
    client: GmailClient = Depends(get_gmail_client),
):
    """Get a specific label."""
    try:
        return await client.get_label(label_id=label_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/labels")
async def create_label(
    name: str,
    message_list_visibility: str = "show",
    label_list_visibility: str = "labelShow",
    client: GmailClient = Depends(get_gmail_client),
):
    """Create a new label."""
    try:
        return await client.create_label(
            name=name,
            message_list_visibility=message_list_visibility,
            label_list_visibility=label_list_visibility,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.delete("/labels/{label_id}")
async def delete_label(
    label_id: str,
    client: GmailClient = Depends(get_gmail_client),
):
    """Delete a label."""
    try:
        await client.delete_label(label_id=label_id)
        return {"status": "deleted", "label_id": label_id}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


# --- Threads ---

@app.get("/threads")
async def list_threads(
    max_results: int = Query(10, ge=1, le=500),
    page_token: Optional[str] = None,
    q: Optional[str] = Query(None, description="Gmail search query"),
    client: GmailClient = Depends(get_gmail_client),
):
    """List threads in user's mailbox."""
    try:
        return await client.list_threads(
            max_results=max_results,
            page_token=page_token,
            q=q,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    format: str = Query("full", enum=["minimal", "full", "metadata"]),
    client: GmailClient = Depends(get_gmail_client),
):
    """Get a specific thread."""
    try:
        return await client.get_thread(thread_id=thread_id, format=format)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/threads/{thread_id}/trash")
async def trash_thread(
    thread_id: str,
    client: GmailClient = Depends(get_gmail_client),
):
    """Move a thread to trash."""
    try:
        return await client.trash_thread(thread_id=thread_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


# --- Drafts ---

@app.get("/drafts")
async def list_drafts(
    max_results: int = Query(10, ge=1, le=500),
    page_token: Optional[str] = None,
    client: GmailClient = Depends(get_gmail_client),
):
    """List drafts."""
    try:
        return await client.list_drafts(max_results=max_results, page_token=page_token)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/drafts")
async def create_draft(
    request: SendMessageRequest,
    client: GmailClient = Depends(get_gmail_client),
):
    """Create a draft."""
    try:
        return await client.create_draft(raw=request.raw, thread_id=request.thread_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/drafts/{draft_id}/send")
async def send_draft(
    draft_id: str,
    client: GmailClient = Depends(get_gmail_client),
):
    """Send a draft."""
    try:
        return await client.send_draft(draft_id=draft_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
