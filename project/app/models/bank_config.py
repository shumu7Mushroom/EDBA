import requests
import logging
from app.models.base import Base
from sqlalchemy import Column, String, Integer, JSON
from sqlalchemy.orm import Session

class BankConfig(Base):
    __tablename__ = 'bank_config'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)  # Associate with the convener's ID
    bank_account = Column(String(64), nullable=False)
    bank_name = Column(String(64), default="EDBA Bank")
    account_name = Column(String(64), default="EDBA System")
    bank_password = Column(String(64), nullable=True)
    balance = Column(Integer, default=0)  # Account balance
    
    # Different access level fee settings
    level1_fee = Column(Integer, default=1)  # Level 1 fee
    level2_fee = Column(Integer, default=2)  # Level 2 fee
    level3_fee = Column(Integer, default=3)  # Level 3 fee
    
    # API configuration fields
    base_url = Column(String(255), nullable=True)
    auth_path = Column(String(255), nullable=True)
    transfer_path = Column(String(255), nullable=True)
    api_config = Column(JSON, nullable=True)  # Store bank API configuration

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
            # Determine if it's a local mock server or an external API based on base_url
            is_local_server = "localhost" in self.base_url or "127.0.0.1" in self.base_url
            transfer_url = f"{self.base_url}{self.transfer_path}"
            
            # Set target account information
            if is_local_server:
                # Use the local mock server's account information
                to_bank = "sdddddа"
                to_name = "ssss"
                to_account = "aaa"
            else:
                # Use the external API's account information
                to_bank = "E-DBA Bank"
                to_name = "E-DBA account"
                to_account = "596117071864958"
            
            # Construct request data
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

        # If not using API or API call fails, use local logic
        admin_config = session.query(BankConfig).filter_by(id=1).first()
        if not admin_config:
            raise ValueError("E-admin account not found")

        self.balance -= amount
        admin_config.balance += amount
        
        logging.info(f"Transferred {amount} from {self.bank_account} to {admin_account} locally")
        logging.info(f"New balances - Sender: {self.balance}, E-admin: {admin_config.balance}")
        
        session.commit()