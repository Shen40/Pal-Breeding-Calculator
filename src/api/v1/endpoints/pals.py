from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.database import get_db 
from src.api.deps import get_breeding_service, get_current_user
from src.services.breeding_service import BreedingService
from src.schemas.pal import UserPalCreate, UserPalResponse
from src.models.user import User

router = APIRouter() 

@router.post("/", response_model=UserPalResponse, status_code=status.HTTP_201_CREATED)
def add_pal(
    pal_in: UserPalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db), 
    service: BreedingService = Depends(get_breeding_service)
):
    db_pal = service.add_pal(db, current_user.id, pal_in)
    return UserPalResponse.model_validate(db_pal)

@router.get("/", response_model=List[UserPalResponse])
def list_pals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: BreedingService = Depends(get_breeding_service)
):
    return service.get_inventory(db, current_user.id)

@router.delete("/{pal_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_pal(
    pal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: BreedingService = Depends(get_breeding_service)
):
    service.delete_pal(db, current_user.id, pal_id)
