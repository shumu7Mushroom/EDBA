import os
import sys

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)

from app import create_app
from app.models.base import db
from app.models.bank_config import BankConfig
from app.models.o_convener import OConvener

app = create_app()

def migrate_bank_configs():
    with app.app_context():
        try:
            # Get all bank configs that don't have a user_id
            configs = BankConfig.query.filter(BankConfig.user_id.is_(None)).all()
            
            if not configs:
                print("No bank configs without user_id found. Nothing to migrate.")
                return
                
            # Get the first approved O-convener to assign as owner
            convener = OConvener.query.filter_by(status_text='approved').first()
            
            if not convener:
                print("Warning: No approved O-convener found. Will use the first O-convener regardless of status.")
                convener = OConvener.query.first()
                
            if not convener:
                print("Error: No O-convener found. Cannot migrate bank configs.")
                return
                
            # Assign the convener as owner of all bank configs
            for config in configs:
                config.user_id = convener.id
                print(f"Assigning bank config #{config.id} to O-convener #{convener.id} ({convener.org_shortname})")
                
            db.session.commit()
            print(f"Successfully migrated {len(configs)} bank config(s) to user_id={convener.id}")
            
        except Exception as e:
            print(f"Error migrating bank configs: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    print("Starting bank config migration...")
    migrate_bank_configs()
    print("Migration completed.")
