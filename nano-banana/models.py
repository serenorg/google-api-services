# ABOUTME: Pydantic models for Nano Banana API request/response schemas.
# ABOUTME: Defines data structures for image generation, editing, and blending.

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request model for image generation."""

    prompt: str = Field(
        ...,
        description="Text description of the image to generate",
        min_length=1,
        max_length=10000,
    )
    aspect_ratio: Literal[
        "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"
    ] = Field(
        default="1:1",
        description="Output aspect ratio",
    )
    resolution: Literal["1k", "2k", "4k"] = Field(
        default="1k",
        description="Output resolution (1k=1024px, 2k=2048px, 4k=4096px)",
    )


class EditRequest(BaseModel):
    """Request model for image editing."""

    image: str = Field(
        ...,
        description="Base64-encoded image data or URL of image to edit",
    )
    prompt: str = Field(
        ...,
        description="Description of edits to make",
        min_length=1,
        max_length=10000,
    )
    mask: Optional[str] = Field(
        default=None,
        description="Optional base64-encoded mask for targeted editing (white=edit, black=preserve)",
    )


class BlendRequest(BaseModel):
    """Request model for image blending."""

    images: List[str] = Field(
        ...,
        description="List of base64-encoded images or URLs to blend (2-14 images)",
        min_length=2,
        max_length=14,
    )
    prompt: str = Field(
        ...,
        description="Description of how to blend the images",
        min_length=1,
        max_length=10000,
    )
    maintain_faces: bool = Field(
        default=True,
        description="Whether to maintain facial consistency for people (up to 5)",
    )


class ImageData(BaseModel):
    """Model for generated image data."""

    data: str = Field(
        ...,
        description="Base64-encoded image data",
    )
    mime_type: str = Field(
        default="image/png",
        description="MIME type of the image",
    )


class GenerateResponse(BaseModel):
    """Response model for image generation/editing/blending."""

    images: List[ImageData] = Field(
        ...,
        description="List of generated images",
    )
    text: Optional[str] = Field(
        default=None,
        description="Optional text response from the model",
    )
