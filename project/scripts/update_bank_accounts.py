import os
import sys

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)

from app import create_app
from app.models.base import db
from app.models.bank_config import BankConfig

app = create_app()

def update_bank_accounts():
    """
    更新所有银行配置的账号信息，使其与模拟服务器中的账号匹配
    """
    with app.app_context():
        try:
            print("正在连接数据库...")
            
            # 查询所有银行配置
            print("正在查询所有银行配置...")
            configs = BankConfig.query.all()
            print(f"查询到 {len(configs)} 个银行配置记录")
            
            if not configs:
                print("没有找到银行配置记录")
                return
                
            accounts = {
                1: {"account": "aaa", "password": "111", "bank_name": "sdddda", "account_name": "ssss"},
                9: {"account": "111", "password": "111", "bank_name": "FutureLearn Federal Bank", "account_name": "11111111"},
                10: {"account": "22222", "password": "222", "bank_name": "FutureLearn Federal Bank", "account_name": "22222"}
            }
            
            count = 0
            for config in configs:
                if config.id in accounts:
                    account_info = accounts[config.id]
                    
                    # 保存旧值以便日志
                    old_account = config.bank_account
                    old_password = config.bank_password
                    
                    # 更新账号信息
                    config.bank_account = account_info["account"]
                    config.bank_password = account_info["password"]
                    config.bank_name = account_info["bank_name"]
                    config.account_name = account_info["account_name"]
                    
                    count += 1
                    print(f"更新配置ID: {config.id}")
                    print(f"  账号: {old_account} -> {config.bank_account}")
                    print(f"  密码: {old_password} -> {config.bank_password}")
                    print(f"  银行: {config.bank_name}")
                    print(f"  账户名: {config.account_name}")
                    print("------------------------")
                
            db.session.commit()
            print(f"成功更新了 {count} 个银行配置账号")
            
        except Exception as e:
            print(f"更新银行账号时发生错误: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    print("开始更新银行配置账号信息...")
    update_bank_accounts()
    print("更新完成。")
