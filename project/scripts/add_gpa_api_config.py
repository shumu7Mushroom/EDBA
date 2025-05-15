"""
为EDBA系统添加GPA查询API配置的脚本
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models.base import db
from app.models.api_config import APIConfig
import datetime

def add_gpa_api_config():
    """添加GPA查询API配置到数据库"""
    app = create_app()
    
    with app.app_context():
        # 查询所有现有配置
        all_configs = APIConfig.query.all()
        print(f"当前数据库中的API配置数量: {len(all_configs)}")
        
        for cfg in all_configs:
            print(f"ID: {cfg.id}, 类型: {cfg.service_type}, 路径: {cfg.path}")
        
        # 检查是否已存在GPA查询配置
        existing_config = APIConfig.query.filter_by(
            service_type='score'
        ).first()
        
        if existing_config:
            print(f"GPA查询API配置已存在 (ID: {existing_config.id})")
            print(f"当前配置: {existing_config.base_url}{existing_config.path} (方法: {existing_config.method})")
            
            # 更新为正确的配置
            if input("是否更新为正确的配置? (y/n): ").lower() == 'y':
                # 使用身份验证接口的相同base_url
                identity_cfg = APIConfig.query.filter_by(service_type='identity').first()
                base_url = identity_cfg.base_url if identity_cfg else 'http://127.0.0.1:5001'
                
                existing_config.base_url = base_url
                existing_config.path = '/api/score'  # 更新为测试服务器的正确路径
                db.session.commit()
                print("GPA查询API配置已更新")
        else:
            print("未找到GPA查询API配置，准备创建...")
            
            # 使用身份验证接口的相同institution_id和base_url
            identity_cfg = APIConfig.query.filter_by(service_type='identity').first()
            institution_id = identity_cfg.institution_id if identity_cfg else 1
            base_url = identity_cfg.base_url if identity_cfg else 'http://127.0.0.1:5001'
            
            # 创建新的GPA查询API配置
            gpa_config = APIConfig(
                institution_id=institution_id,
                service_type='score',
                base_url=base_url,
                path='/api/score',  # 测试服务器的路径
                method='POST',
                input='{"name": "{name}", "id": "{id}"}',
                output=None  # 可以根据实际API响应格式设置
            )
            
            db.session.add(gpa_config)
            db.session.commit()
            print(f"GPA查询API配置添加成功 (ID: {gpa_config.id})")
            print(f"配置: {gpa_config.base_url}{gpa_config.path} (方法: {gpa_config.method})")

if __name__ == '__main__':
    add_gpa_api_config()
