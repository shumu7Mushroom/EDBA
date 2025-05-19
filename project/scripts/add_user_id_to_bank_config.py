import os
import sys

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)

from app import create_app
from app.models.base import db
import sqlalchemy as sa

app = create_app()

def add_user_id_column():
    with app.app_context():
        try:
            # Check if column already exists to avoid errors
            conn = db.engine.connect()
            inspector = sa.inspect(db.engine)
            columns = [column['name'] for column in inspector.get_columns('bank_config')]
            
            if 'user_id' not in columns:
                # Generate and execute the SQL to add the column
                sql = '''
                ALTER TABLE bank_config 
                ADD COLUMN user_id int(11) NULL COMMENT '关联到convener的id' AFTER id;
                '''
                db.session.execute(sa.text(sql))
                db.session.commit()
                print("Successfully added user_id column to bank_config table")
            else:
                print("Column user_id already exists in bank_config table")
        except Exception as e:
            print(f"Error adding user_id column: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    print("Starting bank config table update...")
    add_user_id_column()
    print("Update completed.")