# ABOUTME: HTTP client for Google Calendar API.
# ABOUTME: Handles all requests to Calendar REST API with proper auth.

import httpx
from typing import Optional, Dict, Any, List

import sys
sys.path.insert(0, "..")
from shared.config import get_settings


class CalendarClient:
    """Client for interacting with Google Calendar API."""

    def __init__(self, access_token: str):
        """
        Initialize Calendar client with access token.

        Args:
            access_token: Google OAuth access token
        """
        self.access_token = access_token
        self.settings = get_settings()
        self.base_url = self.settings.calendar_api_base
        self.timeout = self.settings.request_timeout

    def _headers(self) -> Dict[str, str]:
        """Get request headers with authorization."""
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
        """
        Make HTTP request to Calendar API.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path: API path (appended to base URL)
            params: Query parameters
            json: JSON body

        Returns:
            Response JSON as dict

        Raises:
            httpx.HTTPStatusError: If request fails
        """
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

            # DELETE returns empty body
            if response.status_code == 204:
                return {}

            return response.json()

    # Calendar List

    async def list_calendars(
        self,
        max_results: int = 100,
        page_token: Optional[str] = None,
        show_deleted: bool = False,
        show_hidden: bool = False,
    ) -> Dict[str, Any]:
        """List calendars the user has access to."""
        params = {
            "maxResults": max_results,
            "showDeleted": show_deleted,
            "showHidden": show_hidden,
        }
        if page_token:
            params["pageToken"] = page_token
        return await self._request("GET", "/users/me/calendarList", params=params)

    async def get_calendar(self, calendar_id: str) -> Dict[str, Any]:
        """Get a specific calendar."""
        return await self._request("GET", f"/users/me/calendarList/{calendar_id}")

    # Events

    async def list_events(
        self,
        calendar_id: str = "primary",
        max_results: int = 250,
        page_token: Optional[str] = None,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        q: Optional[str] = None,
        single_events: bool = True,
        order_by: str = "startTime",
        show_deleted: bool = False,
    ) -> Dict[str, Any]:
        """List events in a calendar."""
        params = {
            "maxResults": max_results,
            "singleEvents": single_events,
            "orderBy": order_by,
            "showDeleted": show_deleted,
        }
        if page_token:
            params["pageToken"] = page_token
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        if q:
            params["q"] = q
        return await self._request("GET", f"/calendars/{calendar_id}/events", params=params)

    async def get_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        """Get a specific event."""
        return await self._request("GET", f"/calendars/{calendar_id}/events/{event_id}")

    async def create_event(
        self,
        event_data: Dict[str, Any],
        calendar_id: str = "primary",
        send_updates: str = "none",
    ) -> Dict[str, Any]:
        """Create a new event."""
        params = {"sendUpdates": send_updates}
        return await self._request(
            "POST",
            f"/calendars/{calendar_id}/events",
            params=params,
            json=event_data,
        )

    async def update_event(
        self,
        event_id: str,
        event_data: Dict[str, Any],
        calendar_id: str = "primary",
        send_updates: str = "none",
    ) -> Dict[str, Any]:
        """Update an existing event (full update)."""
        params = {"sendUpdates": send_updates}
        return await self._request(
            "PUT",
            f"/calendars/{calendar_id}/events/{event_id}",
            params=params,
            json=event_data,
        )

    async def patch_event(
        self,
        event_id: str,
        event_data: Dict[str, Any],
        calendar_id: str = "primary",
        send_updates: str = "none",
    ) -> Dict[str, Any]:
        """Patch an existing event (partial update)."""
        params = {"sendUpdates": send_updates}
        return await self._request(
            "PATCH",
            f"/calendars/{calendar_id}/events/{event_id}",
            params=params,
            json=event_data,
        )

    async def delete_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        send_updates: str = "none",
    ) -> None:
        """Delete an event."""
        params = {"sendUpdates": send_updates}
        await self._request(
            "DELETE",
            f"/calendars/{calendar_id}/events/{event_id}",
            params=params,
        )

    async def move_event(
        self,
        event_id: str,
        destination_calendar_id: str,
        source_calendar_id: str = "primary",
        send_updates: str = "none",
    ) -> Dict[str, Any]:
        """Move an event to another calendar."""
        params = {
            "destination": destination_calendar_id,
            "sendUpdates": send_updates,
        }
        return await self._request(
            "POST",
            f"/calendars/{source_calendar_id}/events/{event_id}/move",
            params=params,
        )

    # Quick Add

    async def quick_add(
        self,
        text: str,
        calendar_id: str = "primary",
        send_updates: str = "none",
    ) -> Dict[str, Any]:
        """Create event from natural language text."""
        params = {
            "text": text,
            "sendUpdates": send_updates,
        }
        return await self._request(
            "POST",
            f"/calendars/{calendar_id}/events/quickAdd",
            params=params,
        )

    # Free/Busy

    async def query_freebusy(
        self,
        time_min: str,
        time_max: str,
        calendar_ids: List[str],
        time_zone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query free/busy information for calendars."""
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": cal_id} for cal_id in calendar_ids],
        }
        if time_zone:
            body["timeZone"] = time_zone
        return await self._request("POST", "/freeBusy", json=body)

    # Colors

    async def get_colors(self) -> Dict[str, Any]:
        """Get available calendar and event colors."""
        return await self._request("GET", "/colors")

    # Instances (for recurring events)

    async def list_instances(
        self,
        event_id: str,
        calendar_id: str = "primary",
        max_results: int = 250,
        page_token: Optional[str] = None,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List instances of a recurring event."""
        params = {"maxResults": max_results}
        if page_token:
            params["pageToken"] = page_token
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        return await self._request(
            "GET",
            f"/calendars/{calendar_id}/events/{event_id}/instances",
            params=params,
        )
