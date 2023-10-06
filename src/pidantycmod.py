import datetime
from typing import Optional
from pydantic import BaseModel, validator


class ContactBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: str
    birthdate: datetime.date
    additional_info: str = None


class ContactCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: str
    birthdate: str
    additional_info: str = None

    @validator("birthdate")
    def validate_birthdate_format(cls, value):
        try:
            parsed_date = datetime.strptime(value, "%d.%m.%Y").date()
            return parsed_date
        except ValueError:
            raise ValueError('Invalid date format. Please use "dd.mm.yyyy" format.')


class ContactResponse(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: str
    birthdate: datetime.date
    additional_info: Optional[str]


class ContactUpdate(ContactBase):
    pass


class UserCreate(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str


class AvatarResponse(BaseModel):
    avatar_url: str
