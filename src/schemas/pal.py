from typing import List, Optional 
from pydantic import BaseModel, Field, field_validator, ConfigDict
from src.models.pal import Gender 

class UserPalBase(BaseModel):
    species_name: str
    gender: Gender
    passives: List[str] = Field(default_factory=list, max_length=4)
    nickname: Optional[str] = None

    @field_validator("passives")
    @classmethod
    def validate_unique_passives(cls, v: List[str]) -> List[str]:
        if len(v) != len(set(v)):
            raise ValueError("Passive skills must be unique")
        return v
    
class UserPalCreate(UserPalBase):
    pass

class UserPalResponse(UserPalBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)