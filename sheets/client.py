# ABOUTME: HTTP client for Google Sheets API.
# ABOUTME: Handles all requests to Google Sheets REST API with proper auth.

import httpx
from typing import Optional, Dict, Any, List

import sys
sys.path.insert(0, "..")
from shared.config import get_settings


class SheetsClient:
    """Client for interacting with Google Sheets API."""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.settings = get_settings()
        self.base_url = self.settings.sheets_api_base
        self.timeout = self.settings.request_timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self._headers(),
                params=params,
                json=json,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

    # Spreadsheets

    async def create_spreadsheet(
        self,
        title: str,
        sheet_titles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new spreadsheet."""
        body: Dict[str, Any] = {
            "properties": {"title": title},
        }
        if sheet_titles:
            body["sheets"] = [
                {"properties": {"title": t}} for t in sheet_titles
            ]
        return await self._request("POST", "/spreadsheets", json=body)

    async def get_spreadsheet(
        self,
        spreadsheet_id: str,
        include_grid_data: bool = False,
        ranges: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get a spreadsheet by ID."""
        params: Dict[str, Any] = {"includeGridData": include_grid_data}
        if ranges:
            params["ranges"] = ranges
        return await self._request(
            "GET", f"/spreadsheets/{spreadsheet_id}", params=params
        )

    async def batch_update_spreadsheet(
        self,
        spreadsheet_id: str,
        requests: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Apply batch updates to spreadsheet structure."""
        body = {"requests": requests}
        return await self._request(
            "POST",
            f"/spreadsheets/{spreadsheet_id}:batchUpdate",
            json=body,
        )

    # Values

    async def get_values(
        self,
        spreadsheet_id: str,
        range: str,
        major_dimension: str = "ROWS",
        value_render_option: str = "FORMATTED_VALUE",
    ) -> Dict[str, Any]:
        """Get values from a range."""
        params = {
            "majorDimension": major_dimension,
            "valueRenderOption": value_render_option,
        }
        return await self._request(
            "GET",
            f"/spreadsheets/{spreadsheet_id}/values/{range}",
            params=params,
        )

    async def update_values(
        self,
        spreadsheet_id: str,
        range: str,
        values: List[List[Any]],
        value_input_option: str = "USER_ENTERED",
        major_dimension: str = "ROWS",
    ) -> Dict[str, Any]:
        """Update values in a range."""
        params = {"valueInputOption": value_input_option}
        body = {
            "range": range,
            "majorDimension": major_dimension,
            "values": values,
        }
        return await self._request(
            "PUT",
            f"/spreadsheets/{spreadsheet_id}/values/{range}",
            params=params,
            json=body,
        )

    async def append_values(
        self,
        spreadsheet_id: str,
        range: str,
        values: List[List[Any]],
        value_input_option: str = "USER_ENTERED",
        insert_data_option: str = "INSERT_ROWS",
    ) -> Dict[str, Any]:
        """Append values to a range."""
        params = {
            "valueInputOption": value_input_option,
            "insertDataOption": insert_data_option,
        }
        body = {
            "range": range,
            "majorDimension": "ROWS",
            "values": values,
        }
        return await self._request(
            "POST",
            f"/spreadsheets/{spreadsheet_id}/values/{range}:append",
            params=params,
            json=body,
        )

    async def batch_get_values(
        self,
        spreadsheet_id: str,
        ranges: List[str],
        major_dimension: str = "ROWS",
        value_render_option: str = "FORMATTED_VALUE",
    ) -> Dict[str, Any]:
        """Get values from multiple ranges."""
        params = {
            "ranges": ranges,
            "majorDimension": major_dimension,
            "valueRenderOption": value_render_option,
        }
        return await self._request(
            "GET",
            f"/spreadsheets/{spreadsheet_id}/values:batchGet",
            params=params,
        )

    async def batch_update_values(
        self,
        spreadsheet_id: str,
        data: List[Dict[str, Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> Dict[str, Any]:
        """Update values in multiple ranges."""
        body = {
            "valueInputOption": value_input_option,
            "data": data,
        }
        return await self._request(
            "POST",
            f"/spreadsheets/{spreadsheet_id}/values:batchUpdate",
            json=body,
        )

    async def clear_values(
        self,
        spreadsheet_id: str,
        range: str,
    ) -> Dict[str, Any]:
        """Clear values from a range."""
        return await self._request(
            "POST",
            f"/spreadsheets/{spreadsheet_id}/values/{range}:clear",
            json={},
        )
