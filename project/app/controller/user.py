from flask import Blueprint, render_template, request, session
from app.models.student import Student
from app.models.teacher import Teacher
from flask import redirect, url_for
from app.controller.log import log_access

userBP = Blueprint('user', __name__)

@userBP.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', title='Login', header='User Login')

    session.clear()  # ✅ 清除之前登录的 session 信息，防止身份冲突

    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role')

    user = None

    if role == 'student':
        user = Student.query.filter_by(email=email).first()
        valid = user and user._password == password
    elif role == 'teacher':
        user = Teacher.query.filter_by(email=email).first()
        valid = user and user._password == password
    else:
        return render_template('login.html', title='Login', header='User Login', error='请选择有效角色')

    if valid:
        session['user_id'] = user.id
        session['user_role'] = role
        session['user_name'] = user.name
        session['user_org'] = user.organization
        if role == 'student':
            log_access(f"Student login successful (User ID: {user.id})")
            return redirect(url_for('student.dashboard'))
        else:
            log_access(f"Teacher login successful (User ID: {user.id})")
            return redirect(url_for('teacher.dashboard'))

    return render_template('login.html', title='Login', header='User Login', error='邮箱或密码错误')