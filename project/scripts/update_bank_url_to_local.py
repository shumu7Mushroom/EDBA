import os
import sys

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)

from app import create_app
from app.models.base import db
from app.models.bank_config import BankConfig

app = create_app()

def update_base_url_to_local():
    """
    更新所有银行配置的base_url到本地地址，用于测试环境
    """
    with app.app_context():
        try:
            print("正在连接数据库...")
            # 查询所有银行配置
            configs = BankConfig.query.all()
            print(f"找到 {len(configs)} 条银行配置记录")
            
            if not configs:
                print("没有找到银行配置记录")
                return
                
            # 设置本地测试URL (根据你的本地服务端口进行调整)
            local_url = "http://localhost:8001"
            count = 0
            
            for config in configs:
                old_url = config.base_url
                config.base_url = local_url
                count += 1
                print(f"更新配置ID: {config.id}, 旧URL: {old_url} -> 新URL: {local_url}")
                
            db.session.commit()
            print(f"成功将 {count} 个银行配置的base_url更新为本地测试地址: {local_url}")
            
        except Exception as e:
            print(f"更新base_url时发生错误: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    print("开始更新银行配置base_url到本地测试地址...")
    update_base_url_to_local()
    print("更新完成。")
