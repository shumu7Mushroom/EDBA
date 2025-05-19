import os
import sys
import subprocess

def start_server():
    """启动修复后的银行模拟服务器"""
    print("启动修复后的银行模拟服务器...")
    
    # 获取脚本路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(current_dir)
    server_script_path = os.path.join(current_dir, "mock_bank_server.py")
    
    # 添加项目根目录到Python路径
    sys.path.append(project_dir)
    
    # 打印当前目录和服务器脚本路径
    print(f"当前目录: {current_dir}")
    print(f"项目根目录: {project_dir}")
    print(f"服务器脚本路径: {server_script_path}")
    
    # 检查服务器脚本是否存在
    if not os.path.exists(server_script_path):
        print(f"错误: 未找到服务器脚本 {server_script_path}")
        return False
    
    try:
        # 启动服务器
        print("正在启动服务器...")
        print("注意: 服务器将在前台运行。按Ctrl+C终止。")
        print("服务器日志将显示在下方:")
        print("=" * 60)
        
        # 直接使用 Python 解释器运行脚本
        subprocess.run([sys.executable, server_script_path], check=True)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"启动服务器时出错: {e}")
        return False
    except KeyboardInterrupt:
        print("\n服务器已停止")
        return True

if __name__ == "__main__":
    start_server()
