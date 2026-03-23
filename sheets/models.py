# ABOUTME: Pydantic models for Google Sheets API requests and responses.
# ABOUTME: Defines schemas for spreadsheets, values, and batch operations.

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class CreateSpreadsheetRequest(BaseModel):
    """Request to create a new spreadsheet."""
    title: str
    sheet_titles: Optional[List[str]] = Field(
        None,
        alias="sheetTitles",
        description="Optional list of sheet tab names to create",
    )


class UpdateValuesRequest(BaseModel):
    """Request to update cell values in a range."""
    values: List[List[Any]]
    major_dimension: str = Field("ROWS", alias="majorDimension")


class AppendValuesRequest(BaseModel):
    """Request to append rows to a range."""
    values: List[List[Any]]


class BatchUpdateValuesData(BaseModel):
    """A single range + values entry for batch update."""
    range: str
    values: List[List[Any]]
    major_dimension: str = Field("ROWS", alias="majorDimension")


class BatchUpdateValuesRequest(BaseModel):
    """Request to update values across multiple ranges."""
    data: List[BatchUpdateValuesData]
    value_input_option: str = Field("USER_ENTERED", alias="valueInputOption")


class BatchUpdateSpreadsheetRequest(BaseModel):
    """Request to apply structural batch updates to a spreadsheet."""
    requests: List[Dict[str, Any]] = Field(
        ...,
        description="List of update request objects per Google Sheets API spec",
    )


class SpreadsheetProperties(BaseModel):
    """Spreadsheet properties."""
    title: Optional[str] = None
    locale: Optional[str] = None
    auto_recalc: Optional[str] = Field(None, alias="autoRecalc")
    time_zone: Optional[str] = Field(None, alias="timeZone")


class SheetProperties(BaseModel):
    """Properties of a single sheet tab."""
    sheet_id: Optional[int] = Field(None, alias="sheetId")
    title: Optional[str] = None
    index: Optional[int] = None
    sheet_type: Optional[str] = Field(None, alias="sheetType")
    grid_properties: Optional[Dict[str, Any]] = Field(None, alias="gridProperties")


class Sheet(BaseModel):
    """A single sheet within a spreadsheet."""
    properties: Optional[SheetProperties] = None
    data: Optional[List[Dict[str, Any]]] = None


class Spreadsheet(BaseModel):
    """Google Sheets spreadsheet."""
    spreadsheet_id: Optional[str] = Field(None, alias="spreadsheetId")
    properties: Optional[SpreadsheetProperties] = None
    sheets: Optional[List[Sheet]] = None
    spreadsheet_url: Optional[str] = Field(None, alias="spreadsheetUrl")


class ValueRange(BaseModel):
    """Values in a range."""
    range: Optional[str] = None
    major_dimension: Optional[str] = Field(None, alias="majorDimension")
    values: List[List[Any]] = []
