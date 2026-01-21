# ABOUTME: FastAPI application for Google Calendar API service.
# ABOUTME: Exposes REST endpoints that proxy to Google Calendar API.

import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
import httpx

sys.path.insert(0, "..")
from shared.auth import get_token_from_header
from shared.config import get_settings

from client import CalendarClient
from models import CreateEventRequest, UpdateEventRequest, FreeBusyRequest

# Configure logging
settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Calendar API service starting...")
    yield
    logger.info("Calendar API service shutting down...")


app = FastAPI(
    title="Google Calendar API Service",
    description="REST API wrapper for Google Calendar API",
    version="1.0.0",
    lifespan=lifespan,
)


def get_calendar_client(token: str = Depends(get_token_from_header)) -> CalendarClient:
    """Dependency to get Calendar client with user's token."""
    return CalendarClient(access_token=token)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "calendar"}


# --- Calendars ---

@app.get("/calendars")
async def list_calendars(
    max_results: int = Query(100, ge=1, le=250),
    page_token: Optional[str] = None,
    show_deleted: bool = False,
    show_hidden: bool = False,
    client: CalendarClient = Depends(get_calendar_client),
):
    """List calendars the user has access to."""
    try:
        return await client.list_calendars(
            max_results=max_results,
            page_token=page_token,
            show_deleted=show_deleted,
            show_hidden=show_hidden,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.get("/calendars/{calendar_id}")
async def get_calendar(
    calendar_id: str,
    client: CalendarClient = Depends(get_calendar_client),
):
    """Get a specific calendar."""
    try:
        return await client.get_calendar(calendar_id=calendar_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


# --- Events ---

@app.get("/events")
async def list_events(
    calendar_id: str = Query("primary", description="Calendar ID"),
    max_results: int = Query(250, ge=1, le=2500),
    page_token: Optional[str] = None,
    time_min: Optional[str] = Query(None, description="Lower bound (RFC3339)"),
    time_max: Optional[str] = Query(None, description="Upper bound (RFC3339)"),
    q: Optional[str] = Query(None, description="Search query"),
    single_events: bool = Query(True, description="Expand recurring events"),
    order_by: str = Query("startTime", enum=["startTime", "updated"]),
    show_deleted: bool = False,
    client: CalendarClient = Depends(get_calendar_client),
):
    """List events in a calendar."""
    try:
        return await client.list_events(
            calendar_id=calendar_id,
            max_results=max_results,
            page_token=page_token,
            time_min=time_min,
            time_max=time_max,
            q=q,
            single_events=single_events,
            order_by=order_by,
            show_deleted=show_deleted,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.get("/events/{event_id}")
async def get_event(
    event_id: str,
    calendar_id: str = Query("primary"),
    client: CalendarClient = Depends(get_calendar_client),
):
    """Get a specific event by ID."""
    try:
        return await client.get_event(event_id=event_id, calendar_id=calendar_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/events")
async def create_event(
    request: CreateEventRequest,
    calendar_id: str = Query("primary"),
    send_updates: str = Query("none", enum=["all", "externalOnly", "none"]),
    client: CalendarClient = Depends(get_calendar_client),
):
    """Create a new event."""
    try:
        event_data = request.model_dump(by_alias=True, exclude_none=True)
        return await client.create_event(
            event_data=event_data,
            calendar_id=calendar_id,
            send_updates=send_updates,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.put("/events/{event_id}")
async def update_event(
    event_id: str,
    request: UpdateEventRequest,
    calendar_id: str = Query("primary"),
    send_updates: str = Query("none", enum=["all", "externalOnly", "none"]),
    client: CalendarClient = Depends(get_calendar_client),
):
    """Update an existing event (full update)."""
    try:
        event_data = request.model_dump(by_alias=True, exclude_none=True)
        return await client.update_event(
            event_id=event_id,
            event_data=event_data,
            calendar_id=calendar_id,
            send_updates=send_updates,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.patch("/events/{event_id}")
async def patch_event(
    event_id: str,
    request: UpdateEventRequest,
    calendar_id: str = Query("primary"),
    send_updates: str = Query("none", enum=["all", "externalOnly", "none"]),
    client: CalendarClient = Depends(get_calendar_client),
):
    """Patch an existing event (partial update)."""
    try:
        event_data = request.model_dump(by_alias=True, exclude_none=True)
        return await client.patch_event(
            event_id=event_id,
            event_data=event_data,
            calendar_id=calendar_id,
            send_updates=send_updates,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    calendar_id: str = Query("primary"),
    send_updates: str = Query("none", enum=["all", "externalOnly", "none"]),
    client: CalendarClient = Depends(get_calendar_client),
):
    """Delete an event."""
    try:
        await client.delete_event(
            event_id=event_id,
            calendar_id=calendar_id,
            send_updates=send_updates,
        )
        return {"status": "deleted", "event_id": event_id}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/events/{event_id}/move")
async def move_event(
    event_id: str,
    destination: str = Query(..., description="Destination calendar ID"),
    source_calendar_id: str = Query("primary", alias="source"),
    send_updates: str = Query("none", enum=["all", "externalOnly", "none"]),
    client: CalendarClient = Depends(get_calendar_client),
):
    """Move an event to another calendar."""
    try:
        return await client.move_event(
            event_id=event_id,
            destination_calendar_id=destination,
            source_calendar_id=source_calendar_id,
            send_updates=send_updates,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


# --- Quick Add ---

@app.post("/quickAdd")
async def quick_add_event(
    text: str = Query(..., description="Natural language event description"),
    calendar_id: str = Query("primary"),
    send_updates: str = Query("none", enum=["all", "externalOnly", "none"]),
    client: CalendarClient = Depends(get_calendar_client),
):
    """Create event from natural language text."""
    try:
        return await client.quick_add(
            text=text,
            calendar_id=calendar_id,
            send_updates=send_updates,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


# --- Free/Busy ---

@app.post("/freebusy")
async def query_freebusy(
    request: FreeBusyRequest,
    client: CalendarClient = Depends(get_calendar_client),
):
    """Query free/busy information for calendars."""
    try:
        calendar_ids = [item.id for item in request.items]
        return await client.query_freebusy(
            time_min=request.time_min,
            time_max=request.time_max,
            calendar_ids=calendar_ids,
            time_zone=request.time_zone,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


# --- Colors ---

@app.get("/colors")
async def get_colors(client: CalendarClient = Depends(get_calendar_client)):
    """Get available calendar and event colors."""
    try:
        return await client.get_colors()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


# --- Recurring Event Instances ---

@app.get("/events/{event_id}/instances")
async def list_event_instances(
    event_id: str,
    calendar_id: str = Query("primary"),
    max_results: int = Query(250, ge=1, le=2500),
    page_token: Optional[str] = None,
    time_min: Optional[str] = Query(None, description="Lower bound (RFC3339)"),
    time_max: Optional[str] = Query(None, description="Upper bound (RFC3339)"),
    client: CalendarClient = Depends(get_calendar_client),
):
    """List instances of a recurring event."""
    try:
        return await client.list_instances(
            event_id=event_id,
            calendar_id=calendar_id,
            max_results=max_results,
            page_token=page_token,
            time_min=time_min,
            time_max=time_max,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
