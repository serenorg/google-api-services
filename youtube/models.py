# ABOUTME: Defines the supported YouTube list query parameters.
# ABOUTME: Preserves Google's query names and bounds page sizes at fifty items.

from pydantic import BaseModel, Field


class YouTubeQuery(BaseModel):
    """Optional list filters; Google validates endpoint-specific combinations."""

    q: str | None = None
    type: str | None = None
    order: str | None = None
    published_after: str | None = Field(None, alias="publishedAfter")
    published_before: str | None = Field(None, alias="publishedBefore")
    region_code: str | None = Field(None, alias="regionCode")
    relevance_language: str | None = Field(None, alias="relevanceLanguage")
    video_duration: str | None = Field(None, alias="videoDuration")
    event_type: str | None = Field(None, alias="eventType")
    channel_id: str | None = Field(None, alias="channelId")
    playlist_id: str | None = Field(None, alias="playlistId")
    video_id: str | None = Field(None, alias="videoId")
    page_token: str | None = Field(None, alias="pageToken")
    max_results: int | None = Field(None, alias="maxResults", ge=1, le=50)
    part: str = "snippet"
    id: str | None = None
