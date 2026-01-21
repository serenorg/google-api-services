# ABOUTME: Pydantic models for Google Calendar API requests and responses.
# ABOUTME: Defines schemas for calendars, events, and free/busy queries.

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class EventDateTime(BaseModel):
    """Event start/end time."""
    date: Optional[str] = Field(None, description="Date for all-day events (YYYY-MM-DD)")
    date_time: Optional[str] = Field(None, alias="dateTime", description="DateTime with timezone")
    time_zone: Optional[str] = Field(None, alias="timeZone")


class EventAttendee(BaseModel):
    """Event attendee."""
    email: str
    display_name: Optional[str] = Field(None, alias="displayName")
    response_status: Optional[str] = Field(None, alias="responseStatus")
    optional: Optional[bool] = None
    organizer: Optional[bool] = None
    self_: Optional[bool] = Field(None, alias="self")


class EventReminder(BaseModel):
    """Event reminder override."""
    method: str  # "email" or "popup"
    minutes: int


class EventReminders(BaseModel):
    """Event reminders configuration."""
    use_default: Optional[bool] = Field(None, alias="useDefault")
    overrides: Optional[List[EventReminder]] = None


class ConferenceData(BaseModel):
    """Conference/video call data."""
    conference_id: Optional[str] = Field(None, alias="conferenceId")
    conference_solution: Optional[dict] = Field(None, alias="conferenceSolution")
    entry_points: Optional[List[dict]] = Field(None, alias="entryPoints")


class Event(BaseModel):
    """Google Calendar event."""
    id: Optional[str] = None
    status: Optional[str] = None
    html_link: Optional[str] = Field(None, alias="htmlLink")
    created: Optional[str] = None
    updated: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    color_id: Optional[str] = Field(None, alias="colorId")
    creator: Optional[dict] = None
    organizer: Optional[dict] = None
    start: Optional[EventDateTime] = None
    end: Optional[EventDateTime] = None
    recurrence: Optional[List[str]] = None
    recurring_event_id: Optional[str] = Field(None, alias="recurringEventId")
    attendees: Optional[List[EventAttendee]] = None
    reminders: Optional[EventReminders] = None
    conference_data: Optional[ConferenceData] = Field(None, alias="conferenceData")
    visibility: Optional[str] = None
    i_cal_uid: Optional[str] = Field(None, alias="iCalUID")
    sequence: Optional[int] = None


class EventList(BaseModel):
    """List of events response."""
    kind: str = "calendar#events"
    summary: Optional[str] = None
    description: Optional[str] = None
    updated: Optional[str] = None
    time_zone: Optional[str] = Field(None, alias="timeZone")
    access_role: Optional[str] = Field(None, alias="accessRole")
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    next_sync_token: Optional[str] = Field(None, alias="nextSyncToken")
    items: List[Event] = []


class Calendar(BaseModel):
    """Google Calendar."""
    id: str
    summary: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    time_zone: Optional[str] = Field(None, alias="timeZone")
    summary_override: Optional[str] = Field(None, alias="summaryOverride")
    color_id: Optional[str] = Field(None, alias="colorId")
    background_color: Optional[str] = Field(None, alias="backgroundColor")
    foreground_color: Optional[str] = Field(None, alias="foregroundColor")
    selected: Optional[bool] = None
    access_role: Optional[str] = Field(None, alias="accessRole")
    primary: Optional[bool] = None


class CalendarList(BaseModel):
    """List of calendars response."""
    kind: str = "calendar#calendarList"
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    next_sync_token: Optional[str] = Field(None, alias="nextSyncToken")
    items: List[Calendar] = []


class FreeBusyRequestItem(BaseModel):
    """Calendar to query for free/busy."""
    id: str


class FreeBusyRequest(BaseModel):
    """Free/busy query request."""
    time_min: str = Field(..., alias="timeMin", description="Start of query period (RFC3339)")
    time_max: str = Field(..., alias="timeMax", description="End of query period (RFC3339)")
    time_zone: Optional[str] = Field(None, alias="timeZone")
    items: List[FreeBusyRequestItem]


class TimePeriod(BaseModel):
    """Busy time period."""
    start: str
    end: str


class FreeBusyCalendar(BaseModel):
    """Free/busy info for a calendar."""
    busy: List[TimePeriod] = []
    errors: Optional[List[dict]] = None


class FreeBusyResponse(BaseModel):
    """Free/busy query response."""
    kind: str = "calendar#freeBusy"
    time_min: str = Field(..., alias="timeMin")
    time_max: str = Field(..., alias="timeMax")
    calendars: dict = {}  # calendar_id -> FreeBusyCalendar


class CreateEventRequest(BaseModel):
    """Request to create an event."""
    summary: str
    description: Optional[str] = None
    location: Optional[str] = None
    start: EventDateTime
    end: EventDateTime
    attendees: Optional[List[EventAttendee]] = None
    reminders: Optional[EventReminders] = None
    recurrence: Optional[List[str]] = None
    color_id: Optional[str] = Field(None, alias="colorId")
    visibility: Optional[str] = None


class UpdateEventRequest(BaseModel):
    """Request to update an event."""
    summary: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start: Optional[EventDateTime] = None
    end: Optional[EventDateTime] = None
    attendees: Optional[List[EventAttendee]] = None
    reminders: Optional[EventReminders] = None
    recurrence: Optional[List[str]] = None
    color_id: Optional[str] = Field(None, alias="colorId")
    visibility: Optional[str] = None
