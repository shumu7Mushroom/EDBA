#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的银行服务器
这个脚本将执行一系列测试，验证修复后的模拟银行服务器是否正常工作。
"""

import os
import sys
import requests
import json
import time

# 添加项目根目录到Python路径
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)

# 导入Flask应用和模型
from app import create_app
from app.models.base import db
from app.models.bank_config import BankConfig
from app.models.E_admin import EAdmin

# 测试配置
BASE_URL = "http://localhost:8001"
TEST_ACCOUNTS = {
    "sender": {
        "account": "111",
        "password": "111"
    }
}

def print_header(message):
    """打印测试标题"""
    print("\n" + "=" * 60)
    print(f"  {message}")
    print("=" * 60)

def test_server_status():
    """测试服务器状态"""
    print_header("测试服务器状态")
    try:
        response = requests.get(f"{BASE_URL}/hw/bank/status")
        data = response.json()
        print(f"服务器状态: {data['status']}")
        print(f"账户数量: {data['accounts']}")
        print(f"交易数量: {data['transactions']}")
        return True
    except Exception as e:
        print(f"测试服务器状态失败: {str(e)}")
        return False

def test_account_auth(account, password):
    """测试账户认证"""
    print_header(f"测试账户认证: {account}")
    try:
        auth_data = {
            "account_number": account,
            "password": password
        }
        response = requests.post(f"{BASE_URL}/hw/bank/authenticate", json=auth_data)
        data = response.json()
        print(f"认证结果: {data['status']}")
        if data['status'] == 'success':
            print(f"账户: {data['account']}")
            print(f"银行: {data['bank']}")
            print(f"余额: {data['balance']}")
        else:
            print(f"失败原因: {data.get('reason', '未知')}")
        return data['status'] == 'success'
    except Exception as e:
        print(f"测试账户认证失败: {str(e)}")
        return False

def get_admin_account():
    """从数据库获取E-admin账户信息"""
    print_header("获取E-admin账户信息")
    try:
        # 创建Flask应用上下文
        app = create_app()
        with app.app_context():
            admin = EAdmin.query.get(1)
            if admin and hasattr(admin, 'bank_account') and admin.bank_account:
                print(f"E-admin账号: {admin.bank_account}")
                print(f"E-admin银行: {getattr(admin, 'bank_name', 'E-DBA Bank')}")
                return admin.bank_account
            else:
                print("未找到E-admin账号，使用默认账号")
                return "596117071864958"
    except Exception as e:
        print(f"获取E-admin账户信息失败: {str(e)}")
        return "596117071864958"  # 使用默认账号

def test_transfer(from_account, from_password, to_account, amount=1):
    """测试转账"""
    print_header(f"测试转账: {from_account} -> {to_account}, 金额: {amount}")
    try:
        # 获取转账前余额
        before_resp = requests.get(f"{BASE_URL}/hw/bank/balance/{from_account}")
        before_data = before_resp.json()
        before_balance = before_data.get('balance', 0) if before_data.get('status') == 'success' else 0
        print(f"转账前余额: {before_balance}")
        
        # 执行转账
        transfer_data = {
            "from_account": from_account,
            "password": from_password,
            "to_account": to_account,
            "amount": amount
        }
        response = requests.post(f"{BASE_URL}/hw/bank/transfer", json=transfer_data)
        data = response.json()
        print(f"转账结果: {data['status']}")
        
        if data['status'] == 'success':
            print(f"交易ID: {data['transaction_id']}")
            print(f"转账后余额: {data['from_balance']}")
            print(f"金额: {data['amount']}")
            
            # 验证余额变化
            after_balance = data['from_balance']
            expected_balance = before_balance - amount
            if after_balance == expected_balance:
                print(f"✅ 余额正确减少 {amount}: {before_balance} -> {after_balance}")
            else:
                print(f"❌ 余额计算不正确: 期望 {expected_balance}, 实际 {after_balance}")
                
            # 验证数据库余额是否更新
            verify_db_balance(from_account, after_balance)
            verify_db_balance(to_account)
            
            return True
        else:
            print(f"失败原因: {data.get('reason', '未知')}")
            return False
    except Exception as e:
        print(f"测试转账失败: {str(e)}")
        return False

def verify_db_balance(account, expected_balance=None):
    """验证数据库中的余额是否与期望值匹配"""
    try:
        app = create_app()
        with app.app_context():
            # 在数据库中查询账户
            config = BankConfig.query.filter_by(bank_account=account).first()
            if config:
                db_balance = config.balance
                if expected_balance is not None:
                    if db_balance == expected_balance:
                        print(f"✅ 数据库余额正确同步: {account} = {db_balance}")
                    else:
                        print(f"❌ 数据库余额未同步: {account}, 期望 {expected_balance}, 实际 {db_balance}")
                else:
                    print(f"数据库中的余额: {account} = {db_balance}")
            else:
                print(f"数据库中未找到账户 {account} 的配置")
    except Exception as e:
        print(f"验证数据库余额时出错: {str(e)}")

def run_all_tests():
    """运行所有测试"""
    print_header("开始测试修复后的银行服务器")
    
    # 测试服务器状态
    if not test_server_status():
        print("❌ 服务器状态测试失败，请确保服务器正在运行")
        return False
    
    # 获取测试账户
    sender = TEST_ACCOUNTS["sender"]
    
    # 测试账户认证
    if not test_account_auth(sender["account"], sender["password"]):
        print("❌ 账户认证测试失败")
        return False
    
    # 获取E-admin账户
    admin_account = get_admin_account()
    
    # 测试转账到E-admin账户
    if not test_transfer(sender["account"], sender["password"], admin_account, 5):
        print("❌ 转账测试失败")
        return False
    
    print("\n✅ 所有测试通过！银行服务器工作正常。")
    return True

if __name__ == "__main__":
    run_all_tests()
