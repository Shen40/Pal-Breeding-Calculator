from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from src.schemas.pal import UserPalCreate, UserPalResponse

class TargetBreedingRequest(BaseModel):
    target_species: str
    desired_passives: List[str] = Field(default_factory=list, max_length=4)
    require_clean: bool = True
    inventory_override: Optional[List[UserPalCreate]] = None  

class BreedingPairRecommendation(BaseModel):
    male_parent: UserPalResponse
    female_parent: UserPalResponse
    child_species: str
    success_rate: float
    percentage: str
    expected_eggs: float
    p95_eggs: int
    unique_parent_passives: int

    model_config = ConfigDict(from_attributes=True)