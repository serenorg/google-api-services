# ABOUTME: Exposes gateway-authenticated YouTube Data API list routes.
# ABOUTME: Bills returned items exactly and reports exhausted Google quota as 429.

import logging
from decimal import Decimal
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request

from shared.billing import billed
from shared.config import get_settings
from shared.gateway_auth import require_gateway_secret
from youtube.client import YouTubeClient
from youtube.models import YouTubeQuery

# HTTPX request logs include Google's key query parameter.
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(
    title="YouTube API Service",
    description="Gateway-authenticated public YouTube data with per-item billing",
    version="1.0.0",
)


def get_youtube_client(
    gateway: Annotated[None, Depends(require_gateway_secret)],
) -> YouTubeClient:
    """Authenticate before looking up the service-funded Google credential."""
    api_key = get_settings().youtube_api_key
    if not api_key:
        raise HTTPException(status_code=503, detail="YouTube access is not configured")
    return YouTubeClient(api_key)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "youtube"}


@app.get("/search")
@app.get("/videos")
@app.get("/channels")
@app.get("/playlists")
@app.get("/playlistItems")
@app.get("/commentThreads")
async def list_items(
    request: Request,
    query: Annotated[YouTubeQuery, Query()],
    client: Annotated[YouTubeClient, Depends(get_youtube_client)],
):
    """Return one Google result page and charge only for the items it contains."""
    try:
        result = await client.list(
            request.url.path.rsplit("/", 1)[-1],
            query.model_dump(by_alias=True, exclude_none=True),
        )
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        try:
            detail = error.response.json()
        except ValueError:
            detail = {}
        if status == 403 and any(
            item.get("reason") == "quotaExceeded"
            for item in detail.get("error", {}).get("errors", [])
        ):
            status = 429
        raise HTTPException(status_code=status, detail=detail) from None
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="YouTube request timed out") from None
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="YouTube is unavailable") from None
    return billed(result, items=len(result.get("items", [])), unit_price=Decimal("0.004"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8007)
