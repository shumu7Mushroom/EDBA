from sqlalchemy.orm import Session
from app.models.bank_config import BankConfig

def transfer_funds(session: Session, o_convener_account: str, t_admin_account: str, amount: int):
    """
    Handles the transfer of funds from an o-convener to a t-admin.

    :param session: SQLAlchemy session for database operations.
    :param o_convener_account: The bank account of the o-convener.
    :param t_admin_account: The bank account of the t-admin.
    :param amount: The amount to transfer.
    """
    # Fetch the o-convener's bank config
    o_convener = session.query(BankConfig).filter_by(bank_account=o_convener_account).first()
    if not o_convener:
        raise ValueError("o-convener account not found.")

    # Fetch the t-admin's bank config
    t_admin = session.query(BankConfig).filter_by(bank_account=t_admin_account).first()
    if not t_admin:
        raise ValueError("t-admin account not found.")

    # Check if o-convener has sufficient balance
    if o_convener.balance < amount:
        raise ValueError("Insufficient balance in o-convener's account.")

    # Calculate transfer fee (example: using level1_fee for simplicity)
    transfer_fee = o_convener.level1_fee

    # Ensure the total amount including fee is available
    total_deduction = amount + transfer_fee
    if o_convener.balance < total_deduction:
        raise ValueError("Insufficient balance to cover the transfer and fee.")

    # Deduct the amount and fee from o-convener's balance
    o_convener.balance -= total_deduction

    # Add the amount to t-admin's balance
    t_admin.balance += amount

    # Commit the transaction
    session.commit()