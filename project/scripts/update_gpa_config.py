"""
Script to update GPA query API configuration
This script is used to fix previously misconfigured paths
"""
import sys
import os

# Add project path to Python path
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_dir)

from app import create_app
from app.models.base import db
from app.models.api_config import APIConfig
import datetime

def update_gpa_api_config():
    """Update GPA query API configuration to ensure the correct test server URL and path are used"""
    app = create_app()
    
    with app.app_context():
        # Search for GPA query configuration
        score_configs = APIConfig.query.filter_by(service_type='score').all()
        
        if not score_configs:
            print("No GPA query API configuration found, creating new configuration...")
            
            # Search for institution ID
            institution_id = 1  # Default value
            identity_cfg = APIConfig.query.filter_by(service_type='identity').first()
            if identity_cfg:
                institution_id = identity_cfg.institution_id
            
            # Create a new GPA query API configuration - use the test server
            new_config = APIConfig(
                institution_id=institution_id,
                service_type='score',
                base_url='http://127.0.0.1:5001',  # Local test server
                path='/hw/student/record',  # Use the same path as production for consistency
                method='POST',
                created_at=datetime.datetime.now()
            )
            
            db.session.add(new_config)
            db.session.commit()
            print(f"New GPA query API configuration created, ID: {new_config.id}")
            print(f"URL: {new_config.base_url}{new_config.path}")
            return
        
        # Update existing configuration
        for cfg in score_configs:
            print(f"Found GPA query configuration ID: {cfg.id}")
            print(f"Original configuration: {cfg.base_url}{cfg.path} ({cfg.method})")
            
            # Update to test server configuration
            cfg.base_url = 'http://127.0.0.1:5001'  # Local test server
            # Keep the original path unchanged unless it's explicitly incorrect
            if cfg.path != '/hw/student/record' and cfg.path != '/api/score':
                cfg.path = '/hw/student/record'  # Use the same path as production
            
            db.session.commit()
            print(f"Updated to: {cfg.base_url}{cfg.path} ({cfg.method})")

if __name__ == '__main__':
    update_gpa_api_config()
    print("Script execution completed. Please ensure the test server is started: python tests/mock_gpa_server.py")
