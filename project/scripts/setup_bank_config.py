from app import create_app, db
from app.models.bank_config import BankConfig

app = create_app()

with app.app_context():
    # Drop existing bank_config table if it exists
    BankConfig.__table__.drop(db.engine, checkfirst=True)
    
    # Create fresh table
    BankConfig.__table__.create(db.engine)
    
    # Create test bank configuration
    config = BankConfig(
        bank_name='FutureLearn Federal Bank',
        account_name='Utopia Credit Union',
        bank_account='670547811218584',
        bank_password='9978',
        level1_fee=20,  # Default Level 1 fee
        level2_fee=50,  # Default Level 2 fee
        level3_fee=100  # Default Level 3 fee
    )
    
    db.session.add(config)
    db.session.commit()
    
    print("Bank configuration successfully set up with test account credentials.")
