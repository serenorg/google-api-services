# ABOUTME: Pydantic models for Google People (Contacts) API responses.
# ABOUTME: Defines read-only schemas for contacts and contact groups.

from pydantic import BaseModel, Field
from typing import Optional, List


class Name(BaseModel):
    """Person name."""
    given_name: Optional[str] = Field(None, alias="givenName")
    family_name: Optional[str] = Field(None, alias="familyName")
    display_name: Optional[str] = Field(None, alias="displayName")


class EmailAddress(BaseModel):
    """Email address."""
    value: str
    type: Optional[str] = None
    display_name: Optional[str] = Field(None, alias="displayName")


class PhoneNumber(BaseModel):
    """Phone number."""
    value: str
    type: Optional[str] = None


class Organization(BaseModel):
    """Organization (workplace)."""
    name: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None


class Address(BaseModel):
    """Physical address."""
    formatted_value: Optional[str] = Field(None, alias="formattedValue")
    type: Optional[str] = None
    street_address: Optional[str] = Field(None, alias="streetAddress")
    city: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = Field(None, alias="postalCode")
    country: Optional[str] = None
    country_code: Optional[str] = Field(None, alias="countryCode")


class Person(BaseModel):
    """A person/contact resource."""
    resource_name: Optional[str] = Field(None, alias="resourceName")
    etag: Optional[str] = None
    names: Optional[List[Name]] = None
    email_addresses: Optional[List[EmailAddress]] = Field(None, alias="emailAddresses")
    phone_numbers: Optional[List[PhoneNumber]] = Field(None, alias="phoneNumbers")
    organizations: Optional[List[Organization]] = None
    addresses: Optional[List[Address]] = None


class ConnectionsList(BaseModel):
    """List of connections response."""
    connections: List[Person] = []
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    total_people: Optional[int] = Field(None, alias="totalPeople")
    total_items: Optional[int] = Field(None, alias="totalItems")


class ContactGroup(BaseModel):
    """A contact group (label)."""
    resource_name: Optional[str] = Field(None, alias="resourceName")
    etag: Optional[str] = None
    name: Optional[str] = None
    member_count: Optional[int] = Field(None, alias="memberCount")
    group_type: Optional[str] = Field(None, alias="groupType")
