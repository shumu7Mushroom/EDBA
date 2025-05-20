from project.app.models.base import Base
from sqlalchemy import Column, String, Integer, DECIMAL

class BankConfig(Base):
    __tablename__ = 'bank_config'

    id = Column(Integer, primary_key=True)
    bank_account = Column(String(64), nullable=False)
    bank_name = Column(String(64), default="EDBA Bank")
    account_name = Column(String(64), default="EDBA System")
    bank_password = Column(String(64), nullable=True)
    balance = Column(DECIMAL(10,2), default=158888.05)
    auth_path = Column(String(255), nullable=True)
    transfer_path = Column(String(255), nullable=True)