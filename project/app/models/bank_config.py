from app.models.base import Base
from sqlalchemy import Column, String, Integer

class BankConfig(Base):
    __tablename__ = 'bank_config'
    id = Column(Integer, primary_key=True)
    bank_account = Column(String(128), nullable=False)
    fee = Column(Integer, nullable=False, default=0)
