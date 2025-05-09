# app/models/senior_e_admin.py

from app.models.base import Base
from sqlalchemy import Column, Integer, String, Boolean

class SeniorEAdmin(Base):
    __tablename__ = 'senior_e_admin'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    email = Column(String(128), unique=True, nullable=False)
    _password = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)

    def jsonstr(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_active": self.is_active
        }
