# ABOUTME: HTTP client for Google Docs API.
# ABOUTME: Handles all requests to Google Docs REST API with proper auth.

import httpx
from typing import Optional, Dict, Any, List

import sys
sys.path.insert(0, "..")
from shared.config import get_settings


class DocsClient:
    """Client for interacting with Google Docs API."""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.settings = get_settings()
        self.base_url = self.settings.docs_api_base
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

    # Documents

    async def create_document(self, title: str) -> Dict[str, Any]:
        """Create a new document."""
        body = {"title": title}
        return await self._request("POST", "/documents", json=body)

    async def get_document(self, document_id: str) -> Dict[str, Any]:
        """Get a document by ID."""
        return await self._request("GET", f"/documents/{document_id}")

    async def batch_update(
        self,
        document_id: str,
        requests: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Apply a batch of updates to a document."""
        body = {"requests": requests}
        return await self._request(
            "POST",
            f"/documents/{document_id}:batchUpdate",
            json=body,
        )
