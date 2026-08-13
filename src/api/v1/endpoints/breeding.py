from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session 

from src.core.database import get_db
from src.api.deps import get_breeding_service, get_current_user, get_optional_current_user
from src.services.breeding_service import BreedingService 
from src.schemas import TargetBreedingRequest, BreedingPairRecommendation
from src.models.user import User
router = APIRouter() 

class DiscoverRequest(BaseModel):
    inventory_override: Optional[List[Dict[str, Any]]] = None

@router.post("/discover")
def discover_pals(
    req: Optional[DiscoverRequest] = None,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
    service: BreedingService = Depends(get_breeding_service)
) -> Dict[str, List[Dict]]:
    """Returns all breedable child species from either guest inventory or database inventory."""
    # Guest Mode
    if req and req.inventory_override is not None:
        return service.discover_breedable_pals_transient(req.inventory_override)
    
    # Logged-In User Mode
    if current_user:
        return service.discover_breedable_pals(db, current_user.id)

    return {}

@router.post("/find-pairs", response_model=List[BreedingPairRecommendation])
def find_pairs_for_target(
    req: TargetBreedingRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
    service: BreedingService = Depends(get_breeding_service)
):
    if req.inventory_override is not None:
        return service.find_pairs_transient(
            req.inventory_override, req.target_species, req.desired_passives, req.require_clean
        )
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Must be logged in or supply inventory_override"
        )

    return service.find_pairs_for_target(
        db, current_user.id, req.target_species, req.desired_passives, req.require_clean
    )

@router.get("/species", response_model=List[str])
def get_species(service: BreedingService = Depends(get_breeding_service)):
    return service.get_all_species()

@router.get("/passives")
def get_passives(service: BreedingService = Depends(get_breeding_service)) -> List[Dict]:
    return service.get_all_passives()