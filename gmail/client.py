# ABOUTME: HTTP client for Google Gmail API.
# ABOUTME: Handles all requests to Gmail REST API with proper auth.

import httpx
from typing import Optional, Dict, Any

import sys
sys.path.insert(0, "..")
from shared.config import get_settings


class GmailClient:
    """Client for interacting with Google Gmail API."""

    def __init__(self, access_token: str):
        """
        Initialize Gmail client with access token.

        Args:
            access_token: Google OAuth access token
        """
        self.access_token = access_token
        self.settings = get_settings()
        self.base_url = self.settings.gmail_api_base
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
        Make HTTP request to Gmail API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
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
            return response.json()

    # Messages

    async def list_messages(
        self,
        user_id: str = "me",
        max_results: int = 10,
        page_token: Optional[str] = None,
        q: Optional[str] = None,
        label_ids: Optional[list] = None,
    ) -> Dict[str, Any]:
        """List messages in user's mailbox."""
        params = {"maxResults": max_results}
        if page_token:
            params["pageToken"] = page_token
        if q:
            params["q"] = q
        if label_ids:
            params["labelIds"] = label_ids

        return await self._request("GET", f"/users/{user_id}/messages", params=params)

    async def get_message(
        self,
        message_id: str,
        user_id: str = "me",
        format: str = "full",
    ) -> Dict[str, Any]:
        """Get a specific message."""
        params = {"format": format}
        return await self._request("GET", f"/users/{user_id}/messages/{message_id}", params=params)

    async def send_message(
        self,
        raw: str,
        user_id: str = "me",
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a message."""
        body = {"raw": raw}
        if thread_id:
            body["threadId"] = thread_id
        return await self._request("POST", f"/users/{user_id}/messages/send", json=body)

    async def delete_message(
        self,
        message_id: str,
        user_id: str = "me",
    ) -> None:
        """Delete a message permanently."""
        await self._request("DELETE", f"/users/{user_id}/messages/{message_id}")

    async def trash_message(
        self,
        message_id: str,
        user_id: str = "me",
    ) -> Dict[str, Any]:
        """Move message to trash."""
        return await self._request("POST", f"/users/{user_id}/messages/{message_id}/trash")

    async def modify_message(
        self,
        message_id: str,
        add_label_ids: Optional[list] = None,
        remove_label_ids: Optional[list] = None,
        user_id: str = "me",
    ) -> Dict[str, Any]:
        """Modify message labels."""
        body = {}
        if add_label_ids:
            body["addLabelIds"] = add_label_ids
        if remove_label_ids:
            body["removeLabelIds"] = remove_label_ids
        return await self._request("POST", f"/users/{user_id}/messages/{message_id}/modify", json=body)

    # Labels

    async def list_labels(self, user_id: str = "me") -> Dict[str, Any]:
        """List all labels."""
        return await self._request("GET", f"/users/{user_id}/labels")

    async def get_label(self, label_id: str, user_id: str = "me") -> Dict[str, Any]:
        """Get a specific label."""
        return await self._request("GET", f"/users/{user_id}/labels/{label_id}")

    async def create_label(
        self,
        name: str,
        user_id: str = "me",
        message_list_visibility: str = "show",
        label_list_visibility: str = "labelShow",
    ) -> Dict[str, Any]:
        """Create a new label."""
        body = {
            "name": name,
            "messageListVisibility": message_list_visibility,
            "labelListVisibility": label_list_visibility,
        }
        return await self._request("POST", f"/users/{user_id}/labels", json=body)

    async def delete_label(self, label_id: str, user_id: str = "me") -> None:
        """Delete a label."""
        await self._request("DELETE", f"/users/{user_id}/labels/{label_id}")

    # Threads

    async def list_threads(
        self,
        user_id: str = "me",
        max_results: int = 10,
        page_token: Optional[str] = None,
        q: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List threads in user's mailbox."""
        params = {"maxResults": max_results}
        if page_token:
            params["pageToken"] = page_token
        if q:
            params["q"] = q
        return await self._request("GET", f"/users/{user_id}/threads", params=params)

    async def get_thread(
        self,
        thread_id: str,
        user_id: str = "me",
        format: str = "full",
    ) -> Dict[str, Any]:
        """Get a specific thread."""
        params = {"format": format}
        return await self._request("GET", f"/users/{user_id}/threads/{thread_id}", params=params)

    async def trash_thread(
        self,
        thread_id: str,
        user_id: str = "me",
    ) -> Dict[str, Any]:
        """Move thread to trash."""
        return await self._request("POST", f"/users/{user_id}/threads/{thread_id}/trash")

    # Drafts

    async def list_drafts(
        self,
        user_id: str = "me",
        max_results: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List drafts."""
        params = {"maxResults": max_results}
        if page_token:
            params["pageToken"] = page_token
        return await self._request("GET", f"/users/{user_id}/drafts", params=params)

    async def create_draft(
        self,
        raw: str,
        user_id: str = "me",
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a draft."""
        message = {"raw": raw}
        if thread_id:
            message["threadId"] = thread_id
        body = {"message": message}
        return await self._request("POST", f"/users/{user_id}/drafts", json=body)

    async def send_draft(
        self,
        draft_id: str,
        user_id: str = "me",
    ) -> Dict[str, Any]:
        """Send a draft."""
        body = {"id": draft_id}
        return await self._request("POST", f"/users/{user_id}/drafts/send", json=body)
