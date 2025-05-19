import os
import sys

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)

from app import create_app
from app.models.base import db
from app.models.bank_config import BankConfig

app = create_app()

def update_bank_config():
    with app.app_context():
        try:
            # Delete any existing records
            BankConfig.query.delete()
            db.session.commit()
            
            # Create new record with test credentials
            config = BankConfig(
                bank_name='FutureLearn Federal Bank',
                account_name='Utopia Credit Union',
                bank_account='670547811218584',
                bank_password='9978',
                fee=100
            )
            db.session.add(config)
            db.session.commit()
            print("Successfully updated bank configuration")
        except Exception as e:
            print(f"Error updating bank config: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    print("Starting bank config update...")
    update_bank_config()
    print("Update completed.")
