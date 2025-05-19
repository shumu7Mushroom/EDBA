from app.models.base import Base
from sqlalchemy import Column, String, Integer, JSON
from sqlalchemy.orm import Session

class BankConfig(Base):
    __tablename__ = 'bank_config'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)  # 关联到convener的id
    bank_account = Column(String(64), nullable=False)
    bank_name = Column(String(64), default="EDBA Bank")
    account_name = Column(String(64), default="EDBA System")
    bank_password = Column(String(64), nullable=True)
    balance = Column(Integer, default=0)  # 账户余额
    
    # 不同访问级别的费用设置
    level1_fee = Column(Integer, default=1)  # Level 1费用
    level2_fee = Column(Integer, default=2)  # Level 2费用
    level3_fee = Column(Integer, default=3)  # Level 3费用
    
    # API配置字段
    base_url = Column(String(255), nullable=True)
    auth_path = Column(String(255), nullable=True)
    transfer_path = Column(String(255), nullable=True)
    api_config = Column(JSON, nullable=True)  # 存储银行API配置

    def transfer_to_admin(self, session: Session, admin_account: str, amount: int):
        """
        Transfers funds from this bank account to the specified admin account.
        
        :param session: SQLAlchemy session for database operations.
        :param admin_account: The bank account of the e-admin.
        :param amount: The amount to transfer.
        :raises ValueError: If the transfer amount is invalid.
        """
        if amount <= 0:
            raise ValueError("Transfer amount must be greater than zero.")
        
        # 查找 E-admin 账户 (id=1)
        admin_config = session.query(BankConfig).filter_by(id=1).first()
        if not admin_config:
            raise ValueError("E-admin account not found")
            
        # 减少发送方余额
        self.balance -= amount
        
        # 增加 E-admin 账户余额
        admin_config.balance += amount
        
        print(f"Transferring {amount} from {self.bank_account} to {admin_account}")
        print(f"New balances - Sender: {self.balance}, E-admin: {admin_config.balance}")
        
        session.commit()