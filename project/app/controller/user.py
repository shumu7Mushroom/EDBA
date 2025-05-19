from flask import Blueprint, render_template, request, session
from app.models.student import Student
from app.models.teacher import Teacher
from flask import redirect, url_for, flash
from app.controller.log import log_access
from app.models.T_admin import TAdmin
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
    elif role == 't_admin':
        user = TAdmin.query.filter_by(email=email).first()
        valid = user and user._password == password
    else:
        return render_template('login.html', title='Login', header='User Login', error='Please select a valid role')

    if valid:
        # 检查缴费状态
        if role in ['student', 'teacher'] and not getattr(user, 'is_pay', 0):
            return render_template('login.html', title='Login', header='User Login', error='请先缴纳费用')
        session['user_id'] = user.id
        session['user_role'] = role
        session['user_name'] = user.name
        session['user_org'] = user.organization
        if role == 'student':
            log_access(f"Student login successful (User ID: {user.id})")
            return redirect(url_for('student.dashboard'))
        elif role == 'teacher':
            log_access(f"Teacher login successful (User ID: {user.id})")
            return redirect(url_for('teacher.dashboard'))
        elif role == 't_admin':
            log_access(f"T-Admin login successful (User ID: {user.id})")
            return redirect(url_for('tadmin.dashboard'))

    return render_template('login.html', title='Login', header='User Login', error='Incorrect email or password')

@userBP.route('/logout')
def logout():
    session.clear()
    flash("You have successfully logged out")
    return redirect(url_for('user.login'))
