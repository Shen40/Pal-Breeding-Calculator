from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=100)

class UserResponse(UserBase):
    id : int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)