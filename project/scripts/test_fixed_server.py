import requests
import json
import sys
import os
import time

def test_bank_connection(base_url="http://localhost:8001"):
    """测试银行API连接状态"""
    print("=" * 60)
    print(f"测试银行API连接: {base_url}")
    
    try:
        # 首先测试服务器状态
        status_url = f"{base_url}/hw/bank/status"
        print(f"检查服务器状态: {status_url}")
        
        response = requests.get(status_url, timeout=3)
        if response.status_code == 200:
            print("✓ 服务器响应成功!")
            print(f"响应内容: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        else:
            print(f"✗ 服务器响应异常: HTTP {response.status_code}")
            return False
        
        # 测试认证和转账
        test_authenticate_and_transfer(base_url)
        
        return True
    except requests.exceptions.ConnectionError:
        print(f"✗ 连接失败: 无法连接到 {base_url}")
        print("  请确保银行模拟服务器正在运行")
        return False
    except Exception as e:
        print(f"✗ 测试过程中出错: {str(e)}")
        return False

def test_authenticate_and_transfer(base_url):
    """测试认证和转账功能"""
    # 测试账号和密码
    test_accounts = [
        {"account": "aaa", "password": "111"},
        {"account": "111", "password": "111"},
        {"account": "22222", "password": "222"}
    ]
    
    print("\n测试账户认证和转账功能:")
    for account_info in test_accounts:
        account = account_info["account"]
        password = account_info["password"]
        
        print(f"\n账户: {account}")
        
        # 1. 测试认证
        auth_url = f"{base_url}/hw/bank/authenticate"
        auth_data = {
            "bank_account": account,
            "password": password
        }
        
        try:
            auth_response = requests.post(auth_url, json=auth_data, timeout=3)
            if auth_response.status_code == 200:
                auth_result = auth_response.json()
                if auth_result["status"] == "success":
                    print(f"✓ 认证成功! 余额: {auth_result['balance']}")
                    
                    # 2. 测试转账 (转账1元到管理员账户)
                    transfer_url = f"{base_url}/hw/bank/transfer"
                    transfer_data = {
                        "from_account": account,
                        "password": password,
                        "to_account": "596117071864958",  # 管理员账户
                        "amount": 1
                    }
                    
                    transfer_response = requests.post(transfer_url, json=transfer_data, timeout=3)
                    if transfer_response.status_code == 200:
                        transfer_result = transfer_response.json()
                        if transfer_result["status"] == "success":
                            print(f"✓ 转账成功! 新余额: {transfer_result['from_balance']}")
                        else:
                            print(f"✗ 转账失败: {transfer_result['reason']}")
                    else:
                        print(f"✗ 转账请求失败: HTTP {transfer_response.status_code}")
                else:
                    print(f"✗ 认证失败: {auth_result['reason']}")
            else:
                print(f"✗ 认证请求失败: HTTP {auth_response.status_code}")
        except Exception as e:
            print(f"✗ 请求出错: {str(e)}")

def main():
    """主函数"""
    # 第一个参数可以是基础URL，如果没有提供则使用默认值
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
    
    # 测试连接
    if test_bank_connection(base_url):
        print("\n✓ 测试完成！银行API连接正常.")
    else:
        print("\n✗ 测试失败！银行API连接异常.")
        
    print("=" * 60)

if __name__ == "__main__":
    main()
