from app.models.base import Base
from sqlalchemy import Column, String, Integer

class BankConfig(Base):
    __tablename__ = 'bank_config'
    
    id = Column(Integer, primary_key=True)
    bank_account = Column(String(64), nullable=False)
    fee = Column(Integer, nullable=False)
    bank_name = Column(String(64), default="EDBA Bank")
    account_name = Column(String(64), default="EDBA System")

    def __repr__(self):
        return f'<BankConfig {self.bank_name}>'