import requests
import logging
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

    def transfer_to_admin(self, session: Session, admin_account: str, amount: int, use_external_api=True):
        """
        Transfers funds to the admin account using either the local or external API.

        :param session: SQLAlchemy session for database operations.
        :param admin_account: The bank account of the e-admin.
        :param amount: The amount to transfer.
        :param use_external_api: Whether to use the external API for the transfer.
        :raises ValueError: If the transfer amount is invalid or the API call fails.
        """
        if amount <= 0:
            raise ValueError("Transfer amount must be greater than zero.")

        if use_external_api:
            # 根据 base_url 判断是本地模拟服务器还是外部 API
            is_local_server = "localhost" in self.base_url or "127.0.0.1" in self.base_url
            transfer_url = f"{self.base_url}{self.transfer_path}"
            
            # 设置目标账户信息
            if is_local_server:
                # 使用本地模拟服务器的账户信息
                to_bank = "sdddddа"
                to_name = "ssss"
                to_account = "aaa"
            else:
                # 使用外部 API 的账户信息
                to_bank = "E-DBA Bank"
                to_name = "E-DBA account"
                to_account = "596117071864958"
            
            # 构建请求数据
            payload = {
                "from_account": self.bank_account,
                "password": self.bank_password,
                "amount": amount,
                "to_bank": to_bank,
                "to_name": to_name,
                "to_account": to_account
            }

            logging.debug(f"[API] Using {'local' if is_local_server else 'external'} server")
            logging.debug(f"[API] Payload: {payload}")

            try:
                response = requests.post(transfer_url, json=payload, timeout=10)
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get("status") == "success":
                        logging.info("[API] Transfer successful.")
                        return response_data
                    else:
                        reason = response_data.get("reason", "Unknown error")
                        logging.error(f"[API] Transfer failed: {reason}")
                        raise ValueError(f"[API] Transfer failed: {reason}")
                else:
                    logging.error(f"[API] HTTP Error: {response.status_code} - {response.text}")
                    raise ValueError("[API] HTTP Error.")
            except requests.RequestException as e:
                logging.error(f"[API] Request Exception: {e}")
                raise ValueError("[API] Request Exception.")

        # 如果未使用API或API调用失败，使用本地逻辑
        admin_config = session.query(BankConfig).filter_by(id=1).first()
        if not admin_config:
            raise ValueError("E-admin account not found")

        self.balance -= amount
        admin_config.balance += amount
        
        logging.info(f"Transferred {amount} from {self.bank_account} to {admin_account} locally")
        logging.info(f"New balances - Sender: {self.balance}, E-admin: {admin_config.balance}")
        
        session.commit()