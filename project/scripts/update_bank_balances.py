import os
import sys

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)

from app import create_app
from app.models.base import db
from app.models.bank_config import BankConfig

app = create_app()

def update_bank_balances():
    """
    确保所有银行配置有一个初始余额
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
                
            count = 0
            
            for config in configs:
                old_balance = config.balance
                
                # 如果余额为NULL或小于1000，设置为初始值
                if config.balance is None or config.balance < 1000:
                    config.balance = 10000  # 设置一个较大的初始余额
                    count += 1
                    print(f"更新配置ID: {config.id}, 账号: {config.bank_account}, 旧余额: {old_balance} -> 新余额: {config.balance}")
                else:
                    print(f"配置ID: {config.id}, 账号: {config.bank_account}, 当前余额: {config.balance} (无需更新)")
                    
            db.session.commit()
            print(f"成功更新 {count} 个银行配置的余额")
            
        except Exception as e:
            print(f"更新银行余额时发生错误: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    print("开始更新银行配置余额...")
    update_bank_balances()
    print("更新完成。")
