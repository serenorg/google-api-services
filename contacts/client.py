# ABOUTME: HTTP client for Google People (Contacts) API.
# ABOUTME: Handles read-only requests to Google People REST API with proper auth.

import httpx
from typing import Optional, Dict, Any

import sys
sys.path.insert(0, "..")
from shared.config import get_settings


class ContactsClient:
    """Read-only client for interacting with Google People API (Contacts)."""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.settings = get_settings()
        self.base_url = self.settings.contacts_api_base
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
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self._headers(),
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

    # Contacts (People)

    async def list_connections(
        self,
        page_size: int = 100,
        page_token: Optional[str] = None,
        person_fields: str = "names,emailAddresses,phoneNumbers",
        sort_order: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the authenticated user's contacts."""
        params: Dict[str, Any] = {
            "pageSize": page_size,
            "personFields": person_fields,
        }
        if page_token:
            params["pageToken"] = page_token
        if sort_order:
            params["sortOrder"] = sort_order
        return await self._request("GET", "/people/me/connections", params=params)

    async def get_person(
        self,
        resource_name: str,
        person_fields: str = "names,emailAddresses,phoneNumbers,organizations,addresses,biographies",
    ) -> Dict[str, Any]:
        """Get a specific contact by resource name."""
        params = {"personFields": person_fields}
        return await self._request("GET", f"/{resource_name}", params=params)

    async def search_contacts(
        self,
        query: str,
        page_size: int = 30,
        read_mask: str = "names,emailAddresses,phoneNumbers",
    ) -> Dict[str, Any]:
        """Search the user's contacts."""
        params = {
            "query": query,
            "pageSize": page_size,
            "readMask": read_mask,
        }
        return await self._request("GET", "/people:searchContacts", params=params)

    # Contact Groups

    async def list_contact_groups(
        self,
        page_size: int = 200,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List all contact groups."""
        params: Dict[str, Any] = {"pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token
        return await self._request("GET", "/contactGroups", params=params)

    async def get_contact_group(
        self,
        resource_name: str,
        max_members: int = 0,
    ) -> Dict[str, Any]:
        """Get a specific contact group."""
        params: Dict[str, Any] = {"maxMembers": max_members}
        return await self._request("GET", f"/{resource_name}", params=params)
