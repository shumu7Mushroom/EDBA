from flask import Flask, request, jsonify
import os
import sys

# 添加项目根目录到Python路径
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)

# 导入数据库相关模块
from app import create_app
from app.models.base import db
from app.models.bank_config import BankConfig

app = Flask(__name__)
accounts = {}  # 内存中的银行账户

def init_app_context():
    """初始化Flask应用上下文"""
    global accounts
    try:
        flask_app = create_app()
        flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app_context = flask_app.app_context()
        app_context.push()
        db.init_app(flask_app)

        all_configs = BankConfig.query.all()
        for config in all_configs:
            if not config.bank_account:
                continue
            accounts[config.bank_account] = {
                "bank": config.bank_name,
                "account_name": config.account_name,
                "password": config.bank_password or "password123",
                "balance": config.balance or 0
            }

        print(f"✅ 成功加载账户：{len(accounts)} 个")
        return True
    except Exception as e:
        print(f"初始化错误: {str(e)}")
        accounts = {}
        return False

@app.route('/hw/bank/authenticate', methods=['POST'])
def authenticate():
    data = request.json
    account_number = data.get('account_number') or data.get('bank_account') or data.get('from_account')
    password = data.get('password')

    if not account_number and 'from_account' in data:
        account_number = data.get('from_account')

    if account_number not in accounts:
        return jsonify({"status": "error", "reason": "账号不存在"}), 200

    account = accounts[account_number]
    if account["password"] != password:
        return jsonify({"status": "error", "reason": "密码错误"}), 200

    return jsonify({
        "status": "success",
        "account": account_number,
        "bank": account["bank"],
        "balance": account["balance"]
    })

@app.route('/hw/bank/transfer', methods=['POST'])
def transfer():
    data = request.json
    from_account = data.get('from_account') or data.get('bank_account')
    to_account = data.get('to_account')
    password = data.get('password')
    amount = int(data.get('amount', 0))

    print(f"[DEBUG] 转账请求 from={from_account}, to={to_account}, amount={amount}")

    # 查找发送方账户
    sender_config = BankConfig.query.filter_by(bank_account=from_account.strip()).first()
    if not sender_config:
        return jsonify({"status": "error", "reason": "发送方账号不存在"}), 200
    if sender_config.bank_password != password:
        return jsonify({"status": "error", "reason": "密码错误"}), 200
    if sender_config.balance < amount:
        return jsonify({"status": "error", "reason": "余额不足"}), 200

    # ✅ 查找目标账户
    receiver_config = BankConfig.query.filter_by(bank_account=to_account.strip()).first()
    if not receiver_config:
        return jsonify({"status": "error", "reason": "目标账户不存在"}), 200

    print(f"[DEBUG] 接收方账户已找到: {receiver_config.bank_account}")

    # 执行转账
    try:
        sender_config.balance -= amount
        receiver_config.balance += amount
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "reason": f"数据库错误: {str(e)}"}), 200

    # ✅ 更新缓存
    accounts[from_account]["balance"] = sender_config.balance
    if receiver_config.bank_account not in accounts:
        accounts[receiver_config.bank_account] = {
            "bank": receiver_config.bank_name,
            "account_name": receiver_config.account_name,
            "password": receiver_config.bank_password,
            "balance": receiver_config.balance
        }
    else:
        accounts[receiver_config.bank_account]["balance"] = receiver_config.balance

    print(f"[✅ SUCCESS] 已转账 {amount} from {from_account} to {to_account}")
    return jsonify({
        "status": "success",
        "from_balance": sender_config.balance,
        "amount": amount
    }), 200


@app.route('/hw/bank/balance/<account>', methods=['GET'])
def get_balance(account):
    if account not in accounts:
        return jsonify({"status": "error", "reason": "账号不存在"}), 200

    return jsonify({
        "status": "success",
        "account": account,
        "bank": accounts[account]["bank"],
        "balance": accounts[account]["balance"]
    })

if __name__ == '__main__':
    if init_app_context():
        app.run(host='0.0.0.0', port=8001, debug=False)
    else:
        print("❌ 初始化失败，无法启动银行服务")
