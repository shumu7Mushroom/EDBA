from flask import Blueprint, render_template, request, session, redirect, url_for
from app.models.E_admin import EAdmin
from app.models.Senior_E_Admin import SeniorEAdmin
from app.models.o_convener import OConvener
from app.models.base import db
from app.controller.log import log_access  # ✅ 添加日志记录函数

adminBP = Blueprint('admin', __name__)
print("adminBP 路由已加载")

# 登录界面
@adminBP.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        return render_template('admin_login.html')
    
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')

    if role == 'eadmin':
        admin = EAdmin.query.filter_by(email=email, _password=password).first()
    elif role == 'senior':
        admin = SeniorEAdmin.query.filter_by(email=email, _password=password).first()
    else:
        admin = None

    if admin:
        session['admin_id'] = admin.id
        session['admin_role'] = role
        session['admin_name'] = admin.name

        log_access(f"{role} 登录成功（ID: {admin.id}）")  # ✅ 记录登录成功
        return redirect(url_for('admin.dashboard'))
    else:
        log_access(f"{role} 登录失败（email: {email}）")  # ✅ 记录登录失败
        return render_template('admin_login.html', error='Invalid credentials')


# 管理后台界面
@adminBP.route('/dashboard')
def dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))

    role = session.get('admin_role')

    if role == 'eadmin':
        conv_list = OConvener.query.filter_by(status_text='pending').all()
    elif role == 'senior':
        conv_list = OConvener.query.filter_by(status_text='reviewed').all()
    else:
        conv_list = []

    log_access(f"访问管理员后台（角色: {role}）")  # ✅ 记录查看后台
    return render_template('admin_dashboard.html', conv_list=conv_list, role=role)


@adminBP.route('/approve/<int:id>', methods=['POST'])
def approve(id):
    role = session.get('admin_role')
    convener = OConvener.query.get(id)
    if not convener:
        return redirect(url_for('admin.dashboard'))

    if role == 'eadmin':
        convener.status_text = 'reviewed'
        log_access(f"E-Admin 审核通过注册申请（O-Convener ID: {id}）")
    elif role == 'senior':
        convener.status_text = 'approved'
        log_access(f"Senior E-Admin 审核通过注册申请（O-Convener ID: {id}）")

    db.session.commit()
    return redirect(url_for('admin.dashboard'))


@adminBP.route('/admin/reject/<int:id>', methods=['POST'])
def reject(id):
    role = session.get('admin_role')
    convener = OConvener.query.get(id)
    if not convener:
        return redirect(url_for('admin.dashboard'))

    if role in ['eadmin', 'senior']:
        convener.status_text = 'rejected'
        log_access(f"{role} 拒绝了 O-Convener 的申请（ID: {id}）")

    db.session.commit()
    return redirect(url_for('admin.dashboard'))


# 退出
@adminBP.route('/logout')
def logout():
    log_access("管理员退出登录")  # ✅ 记录登出
    session.clear()
    return redirect(url_for('admin.admin_login'))
