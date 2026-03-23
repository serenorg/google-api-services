# ABOUTME: Pydantic models for Google Docs API requests and responses.
# ABOUTME: Defines schemas for documents and batch update requests.

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class CreateDocumentRequest(BaseModel):
    """Request to create a new document."""
    title: str


class InsertTextRequest(BaseModel):
    """Insert text at a location."""
    text: str
    index: int = Field(1, description="The zero-based index in the document body to insert at")


class DeleteContentRangeRequest(BaseModel):
    """Delete content in a range."""
    start_index: int = Field(..., alias="startIndex")
    end_index: int = Field(..., alias="endIndex")


class BatchUpdateRequest(BaseModel):
    """Request to apply batch updates to a document."""
    requests: List[Dict[str, Any]] = Field(
        ...,
        description="List of update request objects per Google Docs API spec",
    )


class Document(BaseModel):
    """Google Docs document."""
    document_id: Optional[str] = Field(None, alias="documentId")
    title: Optional[str] = None
    revision_id: Optional[str] = Field(None, alias="revisionId")
    body: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, Any]] = None
    footers: Optional[Dict[str, Any]] = None
    document_style: Optional[Dict[str, Any]] = Field(None, alias="documentStyle")
    named_styles: Optional[Dict[str, Any]] = Field(None, alias="namedStyles")
    lists: Optional[Dict[str, Any]] = None
    inline_objects: Optional[Dict[str, Any]] = Field(None, alias="inlineObjects")
