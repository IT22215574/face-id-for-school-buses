import base64
import binascii
from typing import Annotated
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r'^[0-9]{10}$')]
Identity = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=30, pattern=r'^[0-9]+V?$')]
Photo = Annotated[str, Field(max_length=2800000)]


class IdentityDetails(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: Name
    phone: Phone
    email: EmailStr = Field(max_length=255)
    nic: Identity
    address: Annotated[str, StringConstraints(min_length=5, max_length=500)]
    id_front: Photo
    id_back: Photo

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()

    @field_validator('id_front', 'id_back')
    @classmethod
    def validate_photo(cls, value):
        try:
            header, encoded = value.split(',', 1)
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            raise ValueError('Upload a valid JPEG or PNG image') from None
        valid = (header == 'data:image/jpeg;base64' and raw.startswith(b'\xff\xd8\xff')) or (header == 'data:image/png;base64' and raw.startswith(b'\x89PNG\r\n\x1a\n'))
        if not valid or len(raw) > 2 * 1024 * 1024:
            raise ValueError('Photos must be JPEG or PNG, at most 2 MB each')
        return value


class DriverRegistrationCreate(IdentityDetails):
    password: str = Field(min_length=8, max_length=72)
    license_front: Photo

    @field_validator('license_front')
    @classmethod
    def validate_license_photo(cls, value):
        return cls.validate_photo(value)

    bus_id: int = Field(gt=0)
    assistant: IdentityDetails | None = None

    @field_validator('password')
    @classmethod
    def validate_password(cls, value):
        if len(value.encode()) > 72 or not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError('Password must contain letters and numbers and be at most 72 bytes')
        return value
