# ABOUTME: FastAPI application for Nano Banana (Gemini Image) API service.
# ABOUTME: Exposes REST endpoints that proxy to Google Gemini 3 Pro Image API.

import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx

sys.path.insert(0, "..")
from shared.config import get_settings

from client import GeminiImageClient
from models import (
    GenerateRequest,
    EditRequest,
    BlendRequest,
    GenerateResponse,
)

# Configure logging
settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Nano Banana API service starting...")
    if not settings.google_ai_studio_api_key:
        logger.warning("GOOGLE_AI_STUDIO_API_KEY not set - API calls will fail")
    yield
    logger.info("Nano Banana API service shutting down...")


app = FastAPI(
    title="Nano Banana API Service",
    description="REST API wrapper for Google Gemini 3 Pro Image (Nano Banana Pro)",
    version="1.0.0",
    lifespan=lifespan,
)


def get_client() -> GeminiImageClient:
    """Get Gemini Image client with API key and model from settings."""
    if not settings.google_ai_studio_api_key:
        raise HTTPException(
            status_code=503,
            detail="Service not configured: GOOGLE_AI_STUDIO_API_KEY not set"
        )
    return GeminiImageClient(
        api_key=settings.google_ai_studio_api_key,
        model=settings.gemini_image_model,
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    has_api_key = bool(settings.google_ai_studio_api_key)
    return {
        "status": "healthy" if has_api_key else "degraded",
        "service": "nano-banana",
        "api_key_configured": has_api_key,
        "model": settings.gemini_image_model,
    }


@app.post("/generate", response_model=GenerateResponse)
async def generate_image(request: GenerateRequest):
    """
    Generate an image from a text prompt.

    - **prompt**: Text description of the image to generate
    - **aspect_ratio**: Output aspect ratio (default: 1:1)
    - **resolution**: Output resolution: 1k, 2k, or 4k (default: 1k)
    """
    client = get_client()
    try:
        result = await client.generate(
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            resolution=request.resolution,
        )
        return result
    except httpx.HTTPStatusError as e:
        logger.error(f"Gemini API error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(f"Generate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/4k", response_model=GenerateResponse)
async def generate_4k_image(request: GenerateRequest):
    """
    Generate a 4K resolution image from a text prompt.

    This endpoint always generates at 4K resolution (4096x4096 base).
    """
    client = get_client()
    try:
        result = await client.generate(
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            resolution="4k",
        )
        return result
    except httpx.HTTPStatusError as e:
        logger.error(f"Gemini API error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(f"Generate 4K error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/edit", response_model=GenerateResponse)
async def edit_image(request: EditRequest):
    """
    Edit an existing image with a text prompt.

    - **image**: Base64-encoded image or URL of image to edit
    - **prompt**: Description of edits to make
    - **mask**: Optional base64-encoded mask for targeted editing
    """
    client = get_client()
    try:
        result = await client.edit(
            image=request.image,
            prompt=request.prompt,
            mask=request.mask,
        )
        return result
    except httpx.HTTPStatusError as e:
        logger.error(f"Gemini API error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(f"Edit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/blend", response_model=GenerateResponse)
async def blend_images(request: BlendRequest):
    """
    Blend multiple images into a cohesive composition.

    - **images**: List of base64-encoded images or URLs (2-14 images)
    - **prompt**: Description of how to blend the images
    - **maintain_faces**: Whether to maintain facial consistency (up to 5 people)
    """
    client = get_client()
    try:
        result = await client.blend(
            images=request.images,
            prompt=request.prompt,
            maintain_faces=request.maintain_faces,
        )
        return result
    except httpx.HTTPStatusError as e:
        logger.error(f"Gemini API error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(f"Blend error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
