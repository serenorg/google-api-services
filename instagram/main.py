# ABOUTME: Serves gateway-authenticated public Instagram profiles, posts and reels.
# ABOUTME: Bills successful items and preserves partial batches when residential proxy blocking pauses reads.

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
    def public_instagram_links(cls, links):
        for link in links:
            url = urlsplit(link)
            if (url.scheme != "https" or url.hostname not in ("www.instagram.com", "instagram.com")
                    or url.username or url.password or url.port not in (None, 443)
                    or any(character.isspace() or ord(character) < 32 for character in link)):
                raise ValueError("Use public HTTPS Instagram links")
        return links


app = FastAPI(title="Instagram Service", version="1.0.0")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "instagram"}


async def read(request, kind):
    for link in request.links:
        path = urlsplit(link).path
        if kind == "profiles" and (not re.fullmatch(r"/[A-Za-z0-9._]{1,30}/?", path)
                or path.strip("/").lower() in {"accounts", "explore", "direct", "stories", "reels", "reel", "p", "tv"}):
            raise HTTPException(status_code=422, detail="Use Instagram profile links")
        if kind == "posts" and not re.fullmatch(r"/(?:p|reel|reels|tv)/[A-Za-z0-9_-]+/?", path):
            raise HTTPException(status_code=422, detail="Use Instagram post or reel links")
    try:
        pool = ProxyPool()
    except ProxyNotConfigured as exc:
        raise HTTPException(status_code=503, detail="Page reading is not configured") from exc
    data = await pool.read_batch(request.links, parse.profile if kind == "profiles" else parse.post)
    return billed(data, sum(item["status"] == "read" for item in data["items"]), Decimal("0.0027"))


@app.post("/profiles", dependencies=[Depends(require_gateway_secret)])
async def profiles(request: LinksRequest):
    return await read(request, "profiles")


@app.post("/posts", dependencies=[Depends(require_gateway_secret)])
async def posts(request: LinksRequest):
    return await read(request, "posts")
