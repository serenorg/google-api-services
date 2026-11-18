# ABOUTME: Validates bounded batches of public website addresses.
# ABOUTME: Limits each detection request to at most twenty-five sites.

from pydantic import BaseModel, Field, HttpUrl, field_validator


class DetectRequest(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=25)

    @field_validator("urls")
    @classmethod
    def reject_credentials(cls, urls):
        if any(url.username is not None or url.password is not None for url in urls):
            raise ValueError("Website addresses must not contain credentials")
        return urls
