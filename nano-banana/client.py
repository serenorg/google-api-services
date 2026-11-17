# ABOUTME: HTTP client for Google Gemini 3 Pro Image (Nano Banana Pro) API.
# ABOUTME: Handles request formatting and response parsing for image generation.

import base64
import httpx
import re
from typing import Optional, List
from urllib.parse import urlparse

from shared.fetch import fetch


class GeminiImageClient:
    """Client for Google Gemini Image API."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    # Available models:
    # - gemini-2.0-flash-exp: Free tier available, good quality
    # - gemini-2.5-flash-preview-05-20: Free tier, latest flash
    # - gemini-3-pro-image-preview: Paid only, highest quality (Nano Banana Pro)
    DEFAULT_MODEL = "gemini-3-pro-image-preview"

    # Resolution mapping to image dimensions
    RESOLUTIONS = {
        "1k": 1024,
        "2k": 2048,
        "4k": 4096,
    }

    def __init__(self, api_key: str, model: Optional[str] = None, timeout: int = 60):
        """
        Initialize the Gemini Image client.

        Args:
            api_key: Google AI Studio API key
            model: Model to use (default: gemini-2.0-flash-exp)
            timeout: Request timeout in seconds (default 60 for image gen)
        """
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL
        self.timeout = timeout

    def _get_endpoint(self) -> str:
        """Get the generateContent endpoint URL."""
        return f"{self.BASE_URL}/models/{self.model}:generateContent"

    def _build_headers(self) -> dict:
        """Build request headers."""
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

    def _is_url(self, s: str) -> bool:
        """Check if string is a URL."""
        try:
            result = urlparse(s)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _is_base64(self, s: str) -> bool:
        """Check if string is base64 encoded."""
        try:
            if len(s) < 100:
                return False
            base64.b64decode(s, validate=True)
            return True
        except Exception:
            return False

    async def _fetch_image_as_base64(self, url: str) -> tuple[str, str]:
        """
        Fetch an image from URL and return as base64.

        Returns:
            Tuple of (base64_data, mime_type)
        """
        response = await fetch(url, timeout=30)
        content_type = response.headers.get("content-type", "image/png")
        mime_type = content_type.split(";")[0].strip()

        base64_data = base64.b64encode(response.content).decode("utf-8")
        return base64_data, mime_type

    def _detect_mime_type(self, base64_data: str) -> str:
        """Detect MIME type from base64 image data."""
        try:
            header = base64.b64decode(base64_data[:32])
            if header.startswith(b"\x89PNG"):
                return "image/png"
            elif header.startswith(b"\xff\xd8\xff"):
                return "image/jpeg"
            elif header.startswith(b"GIF"):
                return "image/gif"
            elif header.startswith(b"RIFF") and b"WEBP" in header:
                return "image/webp"
        except Exception:
            pass
        return "image/png"

    async def _prepare_image_part(self, image: str) -> dict:
        """
        Prepare an image for the API request.

        Args:
            image: Base64-encoded image data or URL

        Returns:
            Image part dict for API request
        """
        if self._is_url(image):
            base64_data, mime_type = await self._fetch_image_as_base64(image)
        else:
            base64_data = image
            mime_type = self._detect_mime_type(image)

        return {
            "inline_data": {
                "mime_type": mime_type,
                "data": base64_data,
            }
        }

    def _parse_response(self, response_data: dict) -> dict:
        """
        Parse the Gemini API response.

        Returns:
            Dict with image data and metadata
        """
        candidates = response_data.get("candidates", [])
        if not candidates:
            raise ValueError("No image generated - empty response")

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])

        result = {
            "images": [],
            "text": None,
        }

        for part in parts:
            # Handle both camelCase (API response) and snake_case formats
            if "inlineData" in part:
                result["images"].append({
                    "data": part["inlineData"]["data"],
                    "mime_type": part["inlineData"]["mimeType"],
                })
            elif "inline_data" in part:
                result["images"].append({
                    "data": part["inline_data"]["data"],
                    "mime_type": part["inline_data"]["mime_type"],
                })
            elif "text" in part:
                result["text"] = part["text"]

        if not result["images"]:
            raise ValueError("No image in response")

        return result

    async def generate(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        resolution: str = "1k",
    ) -> dict:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the image
            aspect_ratio: Output aspect ratio
            resolution: Output resolution (1k, 2k, 4k)

        Returns:
            Dict with generated image data
        """
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {
                    "aspectRatio": aspect_ratio,
                }
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._get_endpoint(),
                headers=self._build_headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return self._parse_response(response.json())

    async def edit(
        self,
        image: str,
        prompt: str,
        mask: Optional[str] = None,
    ) -> dict:
        """
        Edit an existing image with a text prompt.

        Args:
            image: Base64-encoded image or URL
            prompt: Description of edits to make
            mask: Optional mask for targeted editing

        Returns:
            Dict with edited image data
        """
        parts = []

        # Add the source image
        image_part = await self._prepare_image_part(image)
        parts.append(image_part)

        # Add mask if provided
        if mask:
            mask_part = await self._prepare_image_part(mask)
            parts.append({"text": "Use this mask for editing:"})
            parts.append(mask_part)

        # Add the edit prompt
        parts.append({"text": f"Edit this image: {prompt}"})

        payload = {
            "contents": [
                {"parts": parts}
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._get_endpoint(),
                headers=self._build_headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return self._parse_response(response.json())

    async def blend(
        self,
        images: List[str],
        prompt: str,
        maintain_faces: bool = True,
    ) -> dict:
        """
        Blend multiple images into a cohesive composition.

        Args:
            images: List of base64-encoded images or URLs (2-14)
            prompt: Description of how to blend
            maintain_faces: Whether to maintain facial consistency

        Returns:
            Dict with blended image data
        """
        if len(images) < 2:
            raise ValueError("At least 2 images required for blending")
        if len(images) > 14:
            raise ValueError("Maximum 14 images allowed for blending")

        parts = []

        # Add all source images
        for i, image in enumerate(images):
            image_part = await self._prepare_image_part(image)
            parts.append(image_part)

        # Add the blend prompt
        face_instruction = ""
        if maintain_faces:
            face_instruction = " Maintain facial consistency for any people in the images."

        parts.append({
            "text": f"Blend these {len(images)} images into a cohesive composition: {prompt}{face_instruction}"
        })

        payload = {
            "contents": [
                {"parts": parts}
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._get_endpoint(),
                headers=self._build_headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return self._parse_response(response.json())
