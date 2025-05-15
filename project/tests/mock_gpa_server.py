"""
修复GPA查询API配置的路径和处理
"""
from flask import Flask, request, jsonify
from werkzeug.serving import run_simple
import sys
import os

# 创建一个简单的API服务器来模拟GPA查询服务
app = Flask(__name__)

# 模拟学生GPA数据
STUDENTS = {
    "S20230001": {
        "name": "Alice Huang",
        "id": "S20230001",
        "major": "计算机科学与技术",
        "gpa": "3.8",
        "rank": "5/120",
        "courses": [
            {"code": "CS101", "name": "计算机导论", "credits": 3, "score": 92, "grade": "A"},
            {"code": "CS201", "name": "数据结构", "credits": 4, "score": 88, "grade": "B+"},
            {"code": "CS301", "name": "算法设计", "credits": 4, "score": 95, "grade": "A+"},
            {"code": "MA101", "name": "高等数学", "credits": 5, "score": 90, "grade": "A-"}
        ]
    },
    "20230002": {
        "name": "李四",
        "id": "20230002",
        "major": "软件工程",
        "gpa": "3.5",
        "rank": "12/118",
        "courses": []
    }
}

@app.route('/hw/student/record', methods=['GET', 'POST'])
def query_score():
    """模拟GPA查询接口 - 使用实际系统使用的路径"""
    # 获取请求参数
    student_id = request.values.get('id', '')
    student_name = request.values.get('name', '')
    
    print(f"收到查询请求: 姓名={student_name}, 学号={student_id}")
    
    # 查找学生信息
    student = STUDENTS.get(student_id)
    
    if not student:
        print(f"未找到学生信息: {student_id}")
        return jsonify({
            "status": "not_found",
            "message": "未找到该学生信息"
        })
    
    # 返回学生GPA信息
    result = {
        "status": "success",
        **student
    }
    print(f"返回结果: {result}")
    return jsonify(result)

if __name__ == '__main__':
    print("GPA查询模拟服务器已启动，监听端口5001...")
    print("可以测试以下学生:")
    for sid, info in STUDENTS.items():
        print(f"- {info['name']} (学号: {sid})")
    print("\n请在另一个命令行窗口运行Flask应用程序来测试GPA查询功能")
    
    # 启动服务器
    run_simple('127.0.0.1', 5001, app, use_reloader=True, use_debugger=True)
