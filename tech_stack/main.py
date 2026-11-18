# ABOUTME: Serves gateway-authenticated website technology detection.
# ABOUTME: Bills only analysed sites and stops batches with excessive blocking.

from contextlib import asynccontextmanager
from decimal import Decimal
from functools import lru_cache
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
import httpx
from starlette.concurrency import run_in_threadpool

from shared.billing import billed
from shared.fetch import fetch
from shared.gateway_auth import require_gateway_secret

from .match import detect
from .models import DetectRequest
from .rules import RuleSet


@lru_cache
def get_rules() -> RuleSet:
    return RuleSet.load(os.environ.get("TECH_STACK_RULES_DIR", Path(__file__).parent / "rules"))


@asynccontextmanager
async def lifespan(app):
    # A missing or invalid rules bundle must prevent serving paid operations.
    get_rules()
    yield


app = FastAPI(title="Website Technology Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "tech-stack"}


@app.post("/detect", dependencies=[Depends(require_gateway_secret)])
async def detect_sites(request: DetectRequest):
    try:
        rules = get_rules()
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Technology rules are unavailable") from exc
    results = []
    analysed = blocked = attempted = 0
    paused = False
    for url in request.urls:
        url = str(url)
        if paused:
            results.append({"url": url, "status": "skipped"})
            continue
        attempted += 1
        try:
            response = await fetch(url)
            # Challenge pages are not successful site analyses.
            if response.headers.get("cf-mitigated", "").lower() == "challenge" or any(
                marker in response.text.lower() for marker in (
                    "<title>just a moment", "<title>attention required! | cloudflare",
                    "<title>verify you are human", "<title>access denied",
                )
            ):
                blocked += 1
                results.append({"url": url, "status": "blocked"})
            else:
                technologies = await run_in_threadpool(detect, response, rules)
                results.append({
                    "url": url, "final_url": str(response.url),
                    "status": "analysed", "technologies": technologies,
                })
                analysed += 1
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            is_blocked = status in (401, 403, 429)
            blocked += int(is_blocked)
            results.append({"url": url, "status": "blocked" if is_blocked else "error", "http_status": status})
        except (httpx.RequestError, ValueError, TimeoutError):
            results.append({"url": url, "status": "error"})
        paused = blocked / attempted > 0.15
    return billed({"sites": results, "paused": paused}, analysed, Decimal("0.002"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
