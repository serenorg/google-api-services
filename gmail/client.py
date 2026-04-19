# ABOUTME: HTTP client for Google Gmail API.
# ABOUTME: Handles all requests to Gmail REST API with proper auth.

import asyncio
import httpx
from typing import Optional, Dict, Any, List

import sys
sys.path.insert(0, "..")
from shared.config import get_settings


# Headers we surface to agents in enriched list responses. Lower-cased for
# case-insensitive matching against Gmail's payload headers.
_ENRICH_HEADERS = ("From", "To", "Subject", "Date")
_ENRICH_HEADER_LOOKUP = {h.lower(): h.lower() for h in _ENRICH_HEADERS}

# Cap parallel enrichment requests so a maxResults=500 list does not burst
# 500 concurrent calls into Gmail's per-user quota.
_ENRICH_CONCURRENCY = 10


def _extract_headers(message: Dict[str, Any]) -> Dict[str, str]:
    """Pull From/To/Subject/Date out of a Gmail message payload.

    Returns a dict keyed by lower-cased header name. Missing headers are
    omitted rather than returned as empty strings so callers can distinguish
    "header not present" from "header present but empty".
    """
    payload = message.get("payload") or {}
    headers = payload.get("headers") or []
    result: Dict[str, str] = {}
    for header in headers:
        name = (header.get("name") or "").lower()
        if name in _ENRICH_HEADER_LOOKUP:
            result[name] = header.get("value", "")
    return result


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
        enriched: bool = True,
    ) -> Dict[str, Any]:
        """List messages in user's mailbox.

        When ``enriched`` is True (default), each returned message stub is
        decorated with ``snippet``, ``from``, ``to``, ``subject``, ``date``,
        ``labelIds``, and ``internalDate`` so agents can distinguish results
        without making an N+1 follow-up call per message.
        """
        params = {"maxResults": max_results}
        if page_token:
            params["pageToken"] = page_token
        if q:
            params["q"] = q
        if label_ids:
            params["labelIds"] = label_ids

        response = await self._request("GET", f"/users/{user_id}/messages", params=params)

        if enriched and response.get("messages"):
            response["messages"] = await self._enrich_message_stubs(
                response["messages"], user_id
            )
        return response

    async def _fetch_message_metadata(
        self,
        message_id: str,
        user_id: str,
        semaphore: asyncio.Semaphore,
    ) -> Dict[str, Any]:
        """Fetch a single message with format=metadata, bounded by a semaphore."""
        async with semaphore:
            return await self._request(
                "GET",
                f"/users/{user_id}/messages/{message_id}",
                params={
                    "format": "metadata",
                    "metadataHeaders": list(_ENRICH_HEADERS),
                },
            )

    async def _enrich_message_stubs(
        self,
        stubs: List[Dict[str, Any]],
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """Decorate {id, threadId} stubs with metadata fetched in parallel.

        On per-message failure (e.g., message deleted between list and get)
        the original stub is returned so the list call as a whole still
        succeeds.
        """
        semaphore = asyncio.Semaphore(_ENRICH_CONCURRENCY)
        tasks = [
            self._fetch_message_metadata(stub["id"], user_id, semaphore)
            for stub in stubs
            if stub.get("id")
        ]
        metas = await asyncio.gather(*tasks, return_exceptions=True)

        enriched: List[Dict[str, Any]] = []
        for stub, meta in zip(stubs, metas):
            if isinstance(meta, BaseException) or not isinstance(meta, dict):
                enriched.append(stub)
                continue
            headers = _extract_headers(meta)
            enriched.append({
                **stub,
                "snippet": meta.get("snippet", ""),
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "subject": headers.get("subject", ""),
                "date": headers.get("date", ""),
                "labelIds": meta.get("labelIds", []),
                "internalDate": meta.get("internalDate", ""),
            })
        return enriched

    async def get_message(
        self,
        message_id: str,
        user_id: str = "me",
        format: str = "full",
    ) -> Dict[str, Any]:
        """Get a specific message."""
        params = {"format": format}
        return await self._request("GET", f"/users/{user_id}/messages/{message_id}", params=params)

    async def get_attachment(
        self,
        message_id: str,
        attachment_id: str,
        user_id: str = "me",
    ) -> Dict[str, Any]:
        """Download a specific attachment from a message.

        Returns Gmail's MessagePartBody shape: {"size": int, "data": str}
        where ``data`` is base64url-encoded attachment bytes.
        """
        return await self._request(
            "GET",
            f"/users/{user_id}/messages/{message_id}/attachments/{attachment_id}",
        )

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
        enriched: bool = True,
    ) -> Dict[str, Any]:
        """List threads in user's mailbox.

        When ``enriched`` is True (default), each thread stub is decorated
        with ``from``, ``to``, ``subject``, and ``date`` taken from the most
        recent message in the thread. The thread snippet is preserved.
        """
        params = {"maxResults": max_results}
        if page_token:
            params["pageToken"] = page_token
        if q:
            params["q"] = q
        response = await self._request("GET", f"/users/{user_id}/threads", params=params)

        if enriched and response.get("threads"):
            response["threads"] = await self._enrich_thread_stubs(
                response["threads"], user_id
            )
        return response

    async def _fetch_thread_metadata(
        self,
        thread_id: str,
        user_id: str,
        semaphore: asyncio.Semaphore,
    ) -> Dict[str, Any]:
        """Fetch a thread with format=metadata, bounded by a semaphore."""
        async with semaphore:
            return await self._request(
                "GET",
                f"/users/{user_id}/threads/{thread_id}",
                params={
                    "format": "metadata",
                    "metadataHeaders": list(_ENRICH_HEADERS),
                },
            )

    async def _enrich_thread_stubs(
        self,
        stubs: List[Dict[str, Any]],
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """Decorate thread stubs with headers from the most recent message."""
        semaphore = asyncio.Semaphore(_ENRICH_CONCURRENCY)
        tasks = [
            self._fetch_thread_metadata(stub["id"], user_id, semaphore)
            for stub in stubs
            if stub.get("id")
        ]
        metas = await asyncio.gather(*tasks, return_exceptions=True)

        enriched: List[Dict[str, Any]] = []
        for stub, meta in zip(stubs, metas):
            if isinstance(meta, BaseException) or not isinstance(meta, dict):
                enriched.append(stub)
                continue
            messages = meta.get("messages") or []
            # Use the most recent message so the headers reflect the latest
            # state of the thread, which is what an agent ranking by recency
            # would expect to see.
            latest = messages[-1] if messages else {}
            headers = _extract_headers(latest)
            enriched.append({
                **stub,
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "subject": headers.get("subject", ""),
                "date": headers.get("date", ""),
                "messageCount": len(messages),
            })
        return enriched

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
        enriched: bool = True,
    ) -> Dict[str, Any]:
        """List drafts.

        When ``enriched`` is True (default), each draft is decorated with
        ``snippet``, ``to``, ``subject``, and ``date`` from the underlying
        message so agents can identify drafts without N+1 follow-ups.
        """
        params = {"maxResults": max_results}
        if page_token:
            params["pageToken"] = page_token
        response = await self._request("GET", f"/users/{user_id}/drafts", params=params)

        if enriched and response.get("drafts"):
            response["drafts"] = await self._enrich_draft_stubs(
                response["drafts"], user_id
            )
        return response

    async def _fetch_draft_metadata(
        self,
        draft_id: str,
        user_id: str,
        semaphore: asyncio.Semaphore,
    ) -> Dict[str, Any]:
        """Fetch a draft with format=metadata, bounded by a semaphore."""
        async with semaphore:
            return await self._request(
                "GET",
                f"/users/{user_id}/drafts/{draft_id}",
                params={
                    "format": "metadata",
                    "metadataHeaders": list(_ENRICH_HEADERS),
                },
            )

    async def _enrich_draft_stubs(
        self,
        stubs: List[Dict[str, Any]],
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """Decorate draft stubs with snippet/to/subject/date from the message."""
        semaphore = asyncio.Semaphore(_ENRICH_CONCURRENCY)
        tasks = [
            self._fetch_draft_metadata(stub["id"], user_id, semaphore)
            for stub in stubs
            if stub.get("id")
        ]
        metas = await asyncio.gather(*tasks, return_exceptions=True)

        enriched: List[Dict[str, Any]] = []
        for stub, meta in zip(stubs, metas):
            if isinstance(meta, BaseException) or not isinstance(meta, dict):
                enriched.append(stub)
                continue
            message = meta.get("message") or {}
            headers = _extract_headers(message)
            enriched.append({
                **stub,
                "snippet": message.get("snippet", ""),
                "to": headers.get("to", ""),
                "from": headers.get("from", ""),
                "subject": headers.get("subject", ""),
                "date": headers.get("date", ""),
            })
        return enriched

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
