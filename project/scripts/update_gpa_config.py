"""
更新GPA查询API配置的脚本
此脚本用于修复之前配置的错误路径
"""
import sys
import os

# 添加项目路径到Python路径
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_dir)

from app import create_app
from app.models.base import db
from app.models.api_config import APIConfig
import datetime

def update_gpa_api_config():
    """更新GPA查询API配置，确保使用正确的测试服务器URL和路径"""
    app = create_app()
    
    with app.app_context():
        # 查找GPA查询配置
        score_configs = APIConfig.query.filter_by(service_type='score').all()
        
        if not score_configs:
            print("未找到GPA查询API配置，将创建新配置...")
            
            # 查找机构ID
            institution_id = 1  # 默认值
            identity_cfg = APIConfig.query.filter_by(service_type='identity').first()
            if identity_cfg:
                institution_id = identity_cfg.institution_id
            
            # 创建新的GPA查询API配置 - 使用测试服务器
            new_config = APIConfig(
                institution_id=institution_id,
                service_type='score',
                base_url='http://127.0.0.1:5001',  # 本地测试服务器
                path='/hw/student/record',  # 使用与生产环境相同的路径以保持一致性
                method='POST',
                created_at=datetime.datetime.now()
            )
            
            db.session.add(new_config)
            db.session.commit()
            print(f"已创建新的GPA查询API配置，ID: {new_config.id}")
            print(f"URL: {new_config.base_url}{new_config.path}")
            return
        
        # 更新现有配置
        for cfg in score_configs:
            print(f"找到GPA查询配置 ID: {cfg.id}")
            print(f"原配置: {cfg.base_url}{cfg.path} ({cfg.method})")
            
            # 更新为测试服务器配置
            cfg.base_url = 'http://127.0.0.1:5001'  # 本地测试服务器
            # 保持原有路径不变，除非是明显错误的
            if cfg.path != '/hw/student/record' and cfg.path != '/api/score':
                cfg.path = '/hw/student/record'  # 使用与生产环境相同的路径
            
            db.session.commit()
            print(f"已更新为: {cfg.base_url}{cfg.path} ({cfg.method})")

if __name__ == '__main__':
    update_gpa_api_config()
    print("脚本执行完毕。请确保启动测试服务器: python tests/mock_gpa_server.py")
