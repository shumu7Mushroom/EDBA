from flask import Flask, request, jsonify
import random
import time
import os
import sys

# 添加项目根目录到Python路径
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)

# 导入数据库相关模块
from app import create_app
from app.models.base import db
from app.models.bank_config import BankConfig

# 创建一个全局的Flask应用实例
flask_app = create_app()
app_context = flask_app.app_context()
app_context.push()

# 确保设置SQLAlchemy配置
flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app = Flask(__name__)

# 模拟的账户数据
accounts = {
    "aaa": {
        "bank": "sdddda", 
        "account_name": "ssss", 
        "password": "111", 
        "balance": 1000
    },
    "111": {
        "bank": "FutureLearn Federal Bank", 
        "account_name": "11111111", 
        "password": "111", 
        "balance": 5000
    },
    "22222": {
        "bank": "FutureLearn Federal Bank", 
        "account_name": "22222", 
        "password": "222", 
        "balance": 3000
    },
    "596117071864958": {  # 这是E-admin的账号
        "bank": "E-DBA Bank", 
        "account_name": "E-DBA account", 
        "password": "admin123", 
        "balance": 50000
    }
}

@app.route('/hw/bank/authenticate', methods=['POST'])
def authenticate():
    """账户认证接口"""
    data = request.json
    print(f"认证请求数据: {data}")
      # 提取请求数据 - 支持多种格式
    account_number = data.get('account_number') or data.get('bank_account') or data.get('from_account')
    password = data.get('password')
    
    # 如果没有提供账号，但是提供了用于转账的账号，则使用它
    if not account_number and 'from_account' in data:
        account_number = data.get('from_account')
    
    # 模拟网络延迟
    time.sleep(0.5)
    
    # 日志
    print(f"收到认证请求: 账号={account_number}")
    
    # 检查账号是否存在
    if account_number not in accounts:
        return jsonify({
            "status": "error",
            "reason": "账号不存在"
        }), 200
        
    # 验证密码
    account = accounts[account_number]
    if account["password"] != password:
        return jsonify({
            "status": "error",
            "reason": "密码错误"
        }), 200
    
    # 认证成功
    return jsonify({
        "status": "success",
        "account": account_number,
        "bank": account["bank"],
        "balance": account["balance"]
    })

@app.route('/hw/bank/transfer', methods=['POST'])
def transfer():
    """转账接口"""
    data = request.json
    print(f"转账请求数据: {data}")
    
    # 提取请求数据（支持EDBA系统的格式）
    from_account = data.get('from_account') or data.get('bank_account') or data.get('account_number')
    from_password = data.get('password')
    to_account = data.get('to_account')
    
    # 记录详细信息
    print(f"解析出的发送账号: {from_account}")
    
    try:
        amount = int(data.get('amount', 0))
    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "reason": "转账金额必须是有效的数字"
        }), 200
    
    # 打印转账信息
    print(f"收到转账请求: 从账号={from_account} 到账号={to_account}, 金额={amount}")
    
    # 模拟网络延迟
    time.sleep(0.5)
    
    # 检查账号是否存在
    if not from_account or from_account not in accounts:
        print(f"转出账号不存在: {from_account}")
        return jsonify({
            "status": "error",
            "reason": f"转出账号不存在: {from_account}"
        }), 200
        
    if not to_account or to_account not in accounts:
        print(f"转入账号不存在: {to_account}")
        return jsonify({
            "status": "error",
            "reason": f"转入账号不存在: {to_account}"
        }), 200
    
    # 验证密码
    from_acc = accounts[from_account]
    if from_acc["password"] != from_password:
        return jsonify({
            "status": "error",
            "reason": "密码错误"
        }), 200
    
    # 验证余额
    if from_acc["balance"] < amount:
        return jsonify({
            "status": "error",
            "reason": "余额不足"
        }), 200
      
    # 进行转账（模拟）
    from_acc["balance"] -= amount
    accounts[to_account]["balance"] += amount
    
    # 更新数据库中的余额
    update_successful = True
    try:
        update_db_balance(from_account, from_acc["balance"])
        update_db_balance(to_account, accounts[to_account]["balance"])
    except Exception as e:
        update_successful = False
        print(f"数据库更新失败: {str(e)}")
    
    # 即使数据库更新失败，也返回成功，因为内存中的余额已更新
    # 这样我们确保付款流程可以继续
    
    # 打印转账结果
    print(f"转账成功: {from_account}({from_acc['balance']}) -> {to_account}({accounts[to_account]['balance']})")
    
    # 转账成功
    return jsonify({
        "status": "success",
        "transaction_id": f"TX{random.randint(100000, 999999)}",
        "from_balance": from_acc["balance"],
        "amount": amount
    })

# 同步数据库中的银行账户余额到内存账户
def sync_db_balances():
    """从数据库同步银行账户余额到内存"""
    try:
        bank_configs = BankConfig.query.all()
        for config in bank_configs:
            account_number = config.bank_account
            if account_number in accounts:
                # 如果账号存在于内存中，更新余额
                old_balance = accounts[account_number]["balance"]
                accounts[account_number]["balance"] = config.balance or old_balance
                print(f"同步账号 {account_number} 余额: {old_balance} -> {accounts[account_number]['balance']}")
        print(f"成功同步 {len(bank_configs)} 个账户的余额")
    except Exception as e:
        print(f"同步账户余额时出错: {str(e)}")

# 更新数据库中的银行账户余额
def update_db_balance(account_number, new_balance):
    """更新数据库中的银行账户余额"""
    try:
        # 查找匹配的银行配置记录
        config = BankConfig.query.filter_by(bank_account=account_number).first()
        if config:
            old_balance = config.balance
            config.balance = new_balance
            db.session.commit()
            print(f"更新数据库账号 {account_number} 余额: {old_balance} -> {new_balance}")
            return True
        else:
            print(f"数据库中未找到账号: {account_number}")
            return False
    except Exception as e:
        print(f"更新数据库账户余额时出错: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass
        return False

if __name__ == '__main__':
    # 同步数据库余额到内存
    try:
        sync_db_balances()
    except Exception as e:
        print(f"同步账户余额时出错，但将继续启动服务器: {str(e)}")
    
    print("启动模拟银行API服务器在 http://localhost:8001")
    print("支持的API路径:")
    print("  - /hw/bank/authenticate (认证)")
    print("  - /hw/bank/transfer (转账)")
    print("\n可用账号:")
    for acc, details in accounts.items():
        print(f"  - 账号: {acc}, 银行: {details['bank']}, 密码: {details['password']}, 余额: {details['balance']}")
    
    # 为了避免Flask应用的上下文冲突，禁用app的调试模式
    app.run(host='0.0.0.0', port=8001, debug=False)
