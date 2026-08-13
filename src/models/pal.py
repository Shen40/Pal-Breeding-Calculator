import enum 
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Enum as SAEnum, JSON, DateTime, ForeignKey 
from sqlalchemy.orm import relationship 
from src.core.database import Base

class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

class UserPal(Base):
    __tablename__ = "user_pals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), default=1)
    species_name = Column(String(100), nullable=False)
    gender = Column(SAEnum(Gender), nullable=False)
    passives = Column(JSON, default=list)
    nickname = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="pals")