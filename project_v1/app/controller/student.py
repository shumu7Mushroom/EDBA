
from flask import Blueprint,render_template, request
from app.models.base import db
from app.models.student import Student

studentBP = Blueprint('student',__name__)

@studentBP.route('', methods=['GET'])
def get_student():
    with db.auto_commit():
        student = Student('hejing',20,'UIC','hejing@mail.uic.edu.hk','123456')
        # 数据库的insert操作
        db.session.add(student)
    return 'hello student'