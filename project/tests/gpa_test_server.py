"""
GPA查询功能测试脚本
仅用于测试目的
"""
from flask import Flask, request, jsonify

app = Flask(__name__)

# 模拟学生GPA数据
STUDENTS = {
    "20230001": {
        "name": "张三",
        "id": "20230001",
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
        "courses": [
            {"code": "SE101", "name": "软件工程导论", "credits": 3, "score": 85, "grade": "B+"},
            {"code": "SE201", "name": "软件需求分析", "credits": 3, "score": 88, "grade": "B+"},
            {"code": "SE301", "name": "软件测试", "credits": 4, "score": 92, "grade": "A"},
            {"code": "CS101", "name": "计算机导论", "credits": 3, "score": 87, "grade": "B+"}
        ]
    },
    "20230003": {
        "name": "王五",
        "id": "20230003",
        "major": "人工智能",
        "gpa": "4.0",
        "rank": "1/90",
        "courses": [
            {"code": "AI101", "name": "人工智能导论", "credits": 3, "score": 98, "grade": "A+"},
            {"code": "AI201", "name": "机器学习", "credits": 4, "score": 96, "grade": "A+"},
            {"code": "AI301", "name": "深度学习", "credits": 4, "score": 95, "grade": "A+"},
            {"code": "MA202", "name": "概率与统计", "credits": 3, "score": 97, "grade": "A+"}
        ]
    }
}

@app.route('/api/score', methods=['GET', 'POST'])
def query_score():
    """模拟GPA查询接口"""
    # 获取请求参数（支持GET或POST）
    student_id = request.values.get('id')
    student_name = request.values.get('name')
    
    # 简单的模拟验证
    if not student_id or not student_name:
        return jsonify({
            "status": "error",
            "message": "缺少学生ID或姓名"
        })
    
    # 查找学生信息
    student = STUDENTS.get(student_id)
    
    if not student:
        return jsonify({
            "status": "not_found",
            "message": "未找到该学生信息"
        })
    
    # 简单验证姓名是否匹配
    if student["name"] != student_name:
        return jsonify({
            "status": "error",
            "message": "姓名与学号不匹配"
        })
    
    # 返回学生GPA信息
    return jsonify({
        "status": "success",
        **student
    })

if __name__ == '__main__':
    print("GPA查询模拟服务器已启动，监听端口5001...")
    print("可以测试以下学生:")
    for sid, info in STUDENTS.items():
        print(f"- {info['name']} (学号: {sid})")
    app.run(host='127.0.0.1', port=5001, debug=True)
