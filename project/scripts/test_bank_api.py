import requests
import json
import sys
import os

def test_bank_api(base_url="http://localhost:8001"):
    """测试银行API是否正常工作"""
    print("===== 测试银行API =====")
    
    # 测试账号和密码
    test_accounts = [
        {"account": "aaa", "password": "111"},
        {"account": "111", "password": "111"},
        {"account": "22222", "password": "222"}
    ]
    
    admin_account = "596117071864958"
    
    for account_info in test_accounts:
        account = account_info["account"]
        password = account_info["password"]
        
        print(f"\n----- 测试账户: {account} -----")
        
        # 1. 测试认证
        print("1. 测试认证...")
        auth_url = f"{base_url}/hw/bank/authenticate"
        auth_data = {
            "bank_account": account,
            "password": password
        }
        
        try:
            auth_response = requests.post(auth_url, json=auth_data, timeout=5)
            print(f"认证状态码: {auth_response.status_code}")
            
            if auth_response.status_code == 200:
                auth_result = auth_response.json()
                print(f"认证结果: {json.dumps(auth_result, ensure_ascii=False, indent=2)}")
                
                # 认证成功，继续测试转账
                if auth_result.get("status") == "success":
                    # 2. 测试转账
                    print("\n2. 测试转账...")
                    transfer_url = f"{base_url}/hw/bank/transfer"
                    transfer_data = {
                        "from_account": account,
                        "password": password,
                        "to_account": admin_account,
                        "amount": 1  # 转账1元作为测试
                    }
                    
                    try:
                        transfer_response = requests.post(transfer_url, json=transfer_data, timeout=5)
                        print(f"转账状态码: {transfer_response.status_code}")
                        
                        if transfer_response.status_code == 200:
                            transfer_result = transfer_response.json()
                            print(f"转账结果: {json.dumps(transfer_result, ensure_ascii=False, indent=2)}")
                            
                            # 检查是否转账成功
                            if transfer_result.get("status") == "success":
                                print("✅ 转账成功")
                            else:
                                print(f"❌ 转账失败: {transfer_result.get('reason', '未知原因')}")
                        else:
                            print(f"❌ 转账请求失败，状态码: {transfer_response.status_code}")
                    
                    except Exception as e:
                        print(f"❌ 转账请求异常: {str(e)}")
                else:
                    print(f"❌ 认证失败: {auth_result.get('reason', '未知原因')}")
            else:
                print(f"❌ 认证请求失败，状态码: {auth_response.status_code}")
                
        except Exception as e:
            print(f"❌ 认证请求异常: {str(e)}")
    
    print("\n===== 测试完成 =====")

if __name__ == "__main__":
    # 允许通过命令行指定不同的基础URL
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
    test_bank_api(base_url)
