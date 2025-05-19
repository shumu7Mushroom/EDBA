import os
import sys
import requests
import json

# 添加项目根目录到Python路径
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)

# 导入数据库相关模块
from app import create_app
from app.models.base import db
from app.models.bank_config import BankConfig

# 创建应用上下文
app = create_app()
with app.app_context():
    # 获取所有银行配置
    configs = BankConfig.query.all()
    
    print(f"找到 {len(configs)} 个银行配置")
    print("================================================================")
    if len(configs) == 0:
        print("警告: 没有找到任何银行配置！请确保已经运行了update_bank_url_to_local.py脚本")
        print("尝试使用默认值进行测试...")
        
        # 创建临时测试对象
        test_config = BankConfig()
        test_config.id = 0
        test_config.user_id = 0
        test_config.bank_name = "测试银行"
        test_config.account_name = "测试账户"
        test_config.bank_account = "111"  # 使用mock_bank_server中的测试账号
        test_config.bank_password = "111"
        test_config.balance = 5000
        test_config.base_url = "http://localhost:8001"
        test_config.auth_path = "hw/bank/authenticate"
        test_config.transfer_path = "hw/bank/transfer"
        
        # 添加到测试列表
        configs = [test_config]
    
    for config in configs:
        print("\n=====================================================")
        print(f"配置ID: {config.id} | 用户ID: {config.user_id}")
        print(f"银行: {config.bank_name} | 账户: {config.bank_account}")
        print(f"余额: {config.balance}")
        print(f"基础URL: {config.base_url}")
        print(f"认证路径: {config.auth_path}")
        print(f"转账路径: {config.transfer_path}")
        
        # 测试连接
        if config.base_url and config.auth_path:
            try:
                # 格式化URL
                base_url = config.base_url.rstrip('/')
                auth_path = config.auth_path.strip('/')
                
                # 构建完整URL
                auth_url = f"{base_url}/{auth_path}"
                
                # 准备认证数据
                auth_data = {
                    "bank": config.bank_name,
                    "account_name": config.account_name,
                    "account_number": config.bank_account,
                    "bank_account": config.bank_account,  # 添加兼容字段
                    "password": config.bank_password
                }
                
                print(f"\n测试认证请求: {auth_url}")
                print(f"认证数据: {json.dumps(auth_data, ensure_ascii=False)}")
                
                # 发送认证请求
                response = requests.post(auth_url, json=auth_data, timeout=3)
                
                print(f"响应状态码: {response.status_code}")
                print(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"认证状态: {result.get('status', 'unknown')}")
                    
                    # 如果认证成功，测试转账请求
                    if result.get('status') == 'success' and config.transfer_path:
                        transfer_path = config.transfer_path.strip('/')
                        transfer_url = f"{base_url}/{transfer_path}"
                        
                        # 准备转账数据（使用小额测试）
                        transfer_data = {
                            "from_bank": config.bank_name,
                            "from_name": config.account_name,
                            "from_account": config.bank_account,
                            "account_number": config.bank_account,
                            "password": config.bank_password,
                            "to_bank": "E-DBA Bank",
                            "to_name": "E-DBA account",
                            "to_account": "596117071864958",  # E-admin账号
                            "amount": 1  # 只转1元测试
                        }
                        
                        print(f"\n测试转账请求: {transfer_url}")
                        print(f"转账数据: {json.dumps(transfer_data, ensure_ascii=False)}")
                        
                        # 发送转账请求
                        trans_response = requests.post(transfer_url, json=transfer_data, timeout=3)
                        
                        print(f"转账响应状态码: {trans_response.status_code}")
                        print(f"转账响应内容: {trans_response.text}")
                
            except requests.exceptions.Timeout:
                print("\n错误: 请求超时")
            except requests.exceptions.ConnectionError:
                print("\n错误: 连接失败 - 服务器可能未运行或无法访问")
            except Exception as e:
                print(f"\n错误: {str(e)}")
