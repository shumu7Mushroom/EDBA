
from flask import Blueprint,render_template, request
from app.models.base import db
from app.models.teacher import Teacher

teacherBP = Blueprint('teacher',__name__)

@teacherBP.route('', methods=['GET'])
def get_teacher():
    with db.auto_commit():
        teacher = Teacher('Nina',18,'CST','nina@uic.edu.hk','123456')
        # 数据库的insert操作
        db.session.add(teacher)
    
    return 'hello teacher'