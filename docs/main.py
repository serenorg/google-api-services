# ABOUTME: FastAPI application for Google Docs API service.
# ABOUTME: Exposes REST endpoints that proxy to Google Docs API.

import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx

sys.path.insert(0, "..")
from shared.auth import get_token_from_header
from shared.config import get_settings

from client import DocsClient
from models import CreateDocumentRequest, BatchUpdateRequest

# Configure logging
settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Docs API service starting...")
    yield
    logger.info("Docs API service shutting down...")


app = FastAPI(
    title="Google Docs API Service",
    description="REST API wrapper for Google Docs API",
    version="1.0.0",
    lifespan=lifespan,
)


def get_docs_client(token: str = Depends(get_token_from_header)) -> DocsClient:
    """Dependency to get Docs client with user's token."""
    return DocsClient(access_token=token)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "docs"}


# --- Documents ---

@app.post("/documents")
async def create_document(
    request: CreateDocumentRequest,
    client: DocsClient = Depends(get_docs_client),
):
    """Create a new Google Doc."""
    try:
        return await client.create_document(title=request.title)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    client: DocsClient = Depends(get_docs_client),
):
    """Get a document by ID."""
    try:
        return await client.get_document(document_id=document_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/documents/{document_id}:batchUpdate")
async def batch_update_document(
    document_id: str,
    request: BatchUpdateRequest,
    client: DocsClient = Depends(get_docs_client),
):
    """Apply batch updates to a document.

    Accepts the standard Google Docs batchUpdate request body.
    See: https://developers.google.com/docs/api/reference/rest/v1/documents/batchUpdate
    """
    try:
        return await client.batch_update(
            document_id=document_id,
            requests=request.requests,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
