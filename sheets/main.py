# ABOUTME: FastAPI application for Google Sheets API service.
# ABOUTME: Exposes REST endpoints that proxy to Google Sheets API.

import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx

sys.path.insert(0, "..")
from shared.auth import get_token_from_header
from shared.config import get_settings

from client import SheetsClient
from models import (
    CreateSpreadsheetRequest,
    UpdateValuesRequest,
    AppendValuesRequest,
    BatchUpdateValuesRequest,
    BatchUpdateSpreadsheetRequest,
)

# Configure logging
settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Sheets API service starting...")
    yield
    logger.info("Sheets API service shutting down...")


app = FastAPI(
    title="Google Sheets API Service",
    description="REST API wrapper for Google Sheets API",
    version="1.0.0",
    lifespan=lifespan,
)


def get_sheets_client(token: str = Depends(get_token_from_header)) -> SheetsClient:
    """Dependency to get Sheets client with user's token."""
    return SheetsClient(access_token=token)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "sheets"}


# --- Spreadsheets ---

@app.post("/spreadsheets")
async def create_spreadsheet(
    request: CreateSpreadsheetRequest,
    client: SheetsClient = Depends(get_sheets_client),
):
    """Create a new spreadsheet."""
    try:
        return await client.create_spreadsheet(
            title=request.title,
            sheet_titles=request.sheet_titles,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.get("/spreadsheets/{spreadsheet_id}")
async def get_spreadsheet(
    spreadsheet_id: str,
    include_grid_data: bool = Query(False, alias="includeGridData"),
    ranges: Optional[List[str]] = Query(None),
    client: SheetsClient = Depends(get_sheets_client),
):
    """Get a spreadsheet by ID."""
    try:
        return await client.get_spreadsheet(
            spreadsheet_id=spreadsheet_id,
            include_grid_data=include_grid_data,
            ranges=ranges,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/spreadsheets/{spreadsheet_id}:batchUpdate")
async def batch_update_spreadsheet(
    spreadsheet_id: str,
    request: BatchUpdateSpreadsheetRequest,
    client: SheetsClient = Depends(get_sheets_client),
):
    """Apply structural batch updates to a spreadsheet.

    See: https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/batchUpdate
    """
    try:
        return await client.batch_update_spreadsheet(
            spreadsheet_id=spreadsheet_id,
            requests=request.requests,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


# --- Values ---

@app.get("/spreadsheets/{spreadsheet_id}/values/{range:path}")
async def get_values(
    spreadsheet_id: str,
    range: str,
    major_dimension: str = Query("ROWS", alias="majorDimension", enum=["ROWS", "COLUMNS"]),
    value_render_option: str = Query(
        "FORMATTED_VALUE",
        alias="valueRenderOption",
        enum=["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"],
    ),
    client: SheetsClient = Depends(get_sheets_client),
):
    """Get values from a range (e.g. Sheet1!A1:D5)."""
    try:
        return await client.get_values(
            spreadsheet_id=spreadsheet_id,
            range=range,
            major_dimension=major_dimension,
            value_render_option=value_render_option,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.put("/spreadsheets/{spreadsheet_id}/values/{range:path}")
async def update_values(
    spreadsheet_id: str,
    range: str,
    request: UpdateValuesRequest,
    value_input_option: str = Query(
        "USER_ENTERED",
        alias="valueInputOption",
        enum=["RAW", "USER_ENTERED"],
    ),
    client: SheetsClient = Depends(get_sheets_client),
):
    """Update values in a range."""
    try:
        return await client.update_values(
            spreadsheet_id=spreadsheet_id,
            range=range,
            values=request.values,
            value_input_option=value_input_option,
            major_dimension=request.major_dimension,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/spreadsheets/{spreadsheet_id}/values/{range:path}:append")
async def append_values(
    spreadsheet_id: str,
    range: str,
    request: AppendValuesRequest,
    value_input_option: str = Query(
        "USER_ENTERED",
        alias="valueInputOption",
        enum=["RAW", "USER_ENTERED"],
    ),
    insert_data_option: str = Query(
        "INSERT_ROWS",
        alias="insertDataOption",
        enum=["OVERWRITE", "INSERT_ROWS"],
    ),
    client: SheetsClient = Depends(get_sheets_client),
):
    """Append values to a range."""
    try:
        return await client.append_values(
            spreadsheet_id=spreadsheet_id,
            range=range,
            values=request.values,
            value_input_option=value_input_option,
            insert_data_option=insert_data_option,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.get("/spreadsheets/{spreadsheet_id}/values:batchGet")
async def batch_get_values(
    spreadsheet_id: str,
    ranges: List[str] = Query(...),
    major_dimension: str = Query("ROWS", alias="majorDimension", enum=["ROWS", "COLUMNS"]),
    value_render_option: str = Query(
        "FORMATTED_VALUE",
        alias="valueRenderOption",
        enum=["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"],
    ),
    client: SheetsClient = Depends(get_sheets_client),
):
    """Get values from multiple ranges."""
    try:
        return await client.batch_get_values(
            spreadsheet_id=spreadsheet_id,
            ranges=ranges,
            major_dimension=major_dimension,
            value_render_option=value_render_option,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/spreadsheets/{spreadsheet_id}/values:batchUpdate")
async def batch_update_values(
    spreadsheet_id: str,
    request: BatchUpdateValuesRequest,
    client: SheetsClient = Depends(get_sheets_client),
):
    """Update values across multiple ranges."""
    try:
        data = [
            {
                "range": d.range,
                "majorDimension": d.major_dimension,
                "values": d.values,
            }
            for d in request.data
        ]
        return await client.batch_update_values(
            spreadsheet_id=spreadsheet_id,
            data=data,
            value_input_option=request.value_input_option,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/spreadsheets/{spreadsheet_id}/values/{range:path}:clear")
async def clear_values(
    spreadsheet_id: str,
    range: str,
    client: SheetsClient = Depends(get_sheets_client),
):
    """Clear values from a range."""
    try:
        return await client.clear_values(
            spreadsheet_id=spreadsheet_id,
            range=range,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
