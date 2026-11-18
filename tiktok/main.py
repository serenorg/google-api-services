# ABOUTME: Serves gateway-authenticated public TikTok profiles and videos.
# ABOUTME: Bills successful reads and returns skipped links when proxy blocking pauses a batch.

from decimal import Decimal
import re
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from shared.billing import billed
from shared.gateway_auth import require_gateway_secret
from shared.proxy_pool import ProxyNotConfigured, ProxyPool
from . import parse


class LinksRequest(BaseModel):
    links: list[str] = Field(min_length=1, max_length=50)

    @field_validator("links")
    @classmethod
    def public_tiktok_links(cls, links):
        for link in links:
            url = urlsplit(link)
            if (url.scheme != "https" or url.hostname not in (
                "www.tiktok.com", "tiktok.com", "m.tiktok.com", "vm.tiktok.com", "vt.tiktok.com",
            ) or url.username or url.password or url.port not in (None, 443)):
                raise ValueError("Use public HTTPS TikTok links")
        return links


app = FastAPI(title="TikTok Service", version="1.0.0")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "tiktok"}


async def read(request, kind):
    for link in request.links:
        url = urlsplit(link)
        if kind == "profiles" and not re.fullmatch(r"/@[\w.-]+/?", url.path):
            raise HTTPException(status_code=422, detail="Use TikTok profile links")
        if kind == "videos" and url.hostname not in ("vm.tiktok.com", "vt.tiktok.com") and not re.fullmatch(r"/@[\w.-]+/video/\d+/?", url.path):
            raise HTTPException(status_code=422, detail="Use TikTok video links")
    try:
        pool = ProxyPool()
    except ProxyNotConfigured as exc:
        raise HTTPException(status_code=503, detail="Page reading is not configured") from exc
    data = await pool.read_batch(request.links, parse.profile if kind == "profiles" else parse.video)
    return billed(data, sum(item["status"] == "read" for item in data["items"]), Decimal("0.0037"))


@app.post("/profiles", dependencies=[Depends(require_gateway_secret)])
async def profiles(request: LinksRequest):
    return await read(request, "profiles")


@app.post("/videos", dependencies=[Depends(require_gateway_secret)])
async def videos(request: LinksRequest):
    return await read(request, "videos")
