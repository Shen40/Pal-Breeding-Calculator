from typing import Optional 
from fastapi import Depends, Request, HTTPException, status
from fastapi.security import OAuth2PasswordBearer 
from sqlalchemy.orm import Session 
import jwt

from src.core.config import settings
from src.core.database import get_db
from src.models.user import User
from src.schemas.token import TokenPayload 
from src.services.breeding_service import BreedingService 

oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

def get_optional_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme_optional)
) -> Optional[User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            return None
        return db.query(User).filter(User.username == username).first()
    except Exception:
        return None
    
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

def get_current_user(
        db: Session = Depends(get_db),
        token: str = Depends(oauth2_scheme)
) -> User:
    credential_exception =HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers ={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credential_exception
        token_data = TokenPayload(sub=username)
    except jwt.PyJWTError:
        raise credential_exception

    user = db.query(User).filter(User.username == token_data.sub).first()
    if user is None:
        raise credential_exception
    return user

def get_breeding_service(request: Request) -> BreedingService:
    return BreedingService(
        pals_data=request.app.state.pals,
        unique_combos=request.app.state.unique_combos,
        reverse_lookup=request.app.state.reverse_lookup,
        passives_data=request.app.state.passives
    )
