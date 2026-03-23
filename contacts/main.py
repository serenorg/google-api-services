# ABOUTME: FastAPI application for Google Contacts (People) API service.
# ABOUTME: Exposes read-only REST endpoints that proxy to Google People API.

import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
import httpx

sys.path.insert(0, "..")
from shared.auth import get_token_from_header
from shared.config import get_settings

from client import ContactsClient

# Configure logging
settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Contacts API service starting...")
    yield
    logger.info("Contacts API service shutting down...")


app = FastAPI(
    title="Google Contacts API Service",
    description="Read-only REST API wrapper for Google People (Contacts) API",
    version="1.0.0",
    lifespan=lifespan,
)


def get_contacts_client(token: str = Depends(get_token_from_header)) -> ContactsClient:
    """Dependency to get Contacts client with user's token."""
    return ContactsClient(access_token=token)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "contacts"}


# --- Contacts ---

@app.get("/contacts")
async def list_contacts(
    page_size: int = Query(100, ge=1, le=1000, alias="pageSize"),
    page_token: Optional[str] = Query(None, alias="pageToken"),
    person_fields: str = Query(
        "names,emailAddresses,phoneNumbers",
        alias="personFields",
        description="Comma-separated list of person fields to return",
    ),
    sort_order: Optional[str] = Query(
        None,
        alias="sortOrder",
        enum=["LAST_MODIFIED_ASCENDING", "LAST_MODIFIED_DESCENDING", "FIRST_NAME_ASCENDING", "LAST_NAME_ASCENDING"],
    ),
    client: ContactsClient = Depends(get_contacts_client),
):
    """List the authenticated user's contacts."""
    try:
        return await client.list_connections(
            page_size=page_size,
            page_token=page_token,
            person_fields=person_fields,
            sort_order=sort_order,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.get("/contacts/search")
async def search_contacts(
    query: str = Query(..., description="Search query string"),
    page_size: int = Query(30, ge=1, le=30, alias="pageSize"),
    read_mask: str = Query(
        "names,emailAddresses,phoneNumbers",
        alias="readMask",
    ),
    client: ContactsClient = Depends(get_contacts_client),
):
    """Search the user's contacts."""
    try:
        return await client.search_contacts(
            query=query,
            page_size=page_size,
            read_mask=read_mask,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.get("/contacts/{resource_name:path}")
async def get_contact(
    resource_name: str,
    person_fields: str = Query(
        "names,emailAddresses,phoneNumbers,organizations,addresses,biographies",
        alias="personFields",
    ),
    client: ContactsClient = Depends(get_contacts_client),
):
    """Get a specific contact (resource_name e.g. people/c123456)."""
    try:
        return await client.get_person(
            resource_name=resource_name,
            person_fields=person_fields,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


# --- Contact Groups ---

@app.get("/contactGroups")
async def list_contact_groups(
    page_size: int = Query(200, ge=1, le=1000, alias="pageSize"),
    page_token: Optional[str] = Query(None, alias="pageToken"),
    client: ContactsClient = Depends(get_contacts_client),
):
    """List all contact groups (labels)."""
    try:
        return await client.list_contact_groups(
            page_size=page_size,
            page_token=page_token,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.get("/contactGroups/{resource_name:path}")
async def get_contact_group(
    resource_name: str,
    max_members: int = Query(0, alias="maxMembers"),
    client: ContactsClient = Depends(get_contacts_client),
):
    """Get a specific contact group."""
    try:
        return await client.get_contact_group(
            resource_name=resource_name,
            max_members=max_members,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
