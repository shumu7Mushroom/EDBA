import os
import sys

print("Script starting...")

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)
print(f"Added {project_dir} to Python path")

try:
    from app import create_app
    from app.models.base import db
    from app.models.bank_config import BankConfig
    from sqlalchemy import text
    print("Successfully imported required modules")
except Exception as e:
    print(f"Error importing modules: {str(e)}")
    sys.exit(1)

app = create_app()
print("Created Flask app")

def recreate_bank_config():
    print("Starting recreate_bank_config function")
    with app.app_context():
        try:
            # Drop existing table
            print("Attempting to drop existing table...")
            db.session.execute(text("DROP TABLE IF EXISTS bank_config"))
            db.session.commit()
            print("Dropped existing bank_config table")
            
            # Create table from model
            print("Creating new table from model...")
            BankConfig.__table__.create(db.engine)
            print("Created new bank_config table")
            
            # Insert test data
            print("Inserting test configuration...")
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
            print("Added test configuration successfully")
            
        except Exception as e:
            print(f"Error in recreate_bank_config: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    print("Starting bank config table recreation...")
    try:
        recreate_bank_config()
        print("Process completed successfully.")
    except Exception as e:
        print(f"Process failed: {str(e)}")
        sys.exit(1)
