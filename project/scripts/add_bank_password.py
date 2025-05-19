import os
import sys

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)

from app import create_app
from app.models.base import db
import pymysql
from sqlalchemy import text

app = create_app()

def check_column_exists():
    with app.app_context():
        try:
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'bank_config' 
                AND COLUMN_NAME = 'bank_password'
            """))
            exists = result.fetchone() is not None
            print(f"Column bank_password exists: {exists}")
            return exists
        except Exception as e:
            print(f"Error checking column: {e}")
            return False

def add_column():
    with app.app_context():
        try:
            # First try to check if column exists
            if not check_column_exists():
                print("Adding bank_password column...")
                # Execute the ALTER TABLE command
                db.session.execute(text("""
                    ALTER TABLE bank_config 
                    ADD COLUMN bank_password VARCHAR(64) NULL DEFAULT NULL
                """))
                db.session.commit()
                print("Successfully added bank_password column")
            else:
                print("Column already exists")
        except Exception as e:
            print(f"Error adding column: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    print("Starting script...")
    add_column()
    print("Script completed.")
