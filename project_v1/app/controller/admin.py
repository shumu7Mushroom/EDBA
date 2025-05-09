from flask import Blueprint, render_template, request, session, redirect, url_for
from app.models.E_admin import EAdmin
from app.models.Senior_E_Admin import SeniorEAdmin
from app.models.o_convener import OConvener
from app.models.base import db

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
        return redirect(url_for('admin.dashboard'))
    else:
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

    return render_template('admin_dashboard.html', conv_list=conv_list, role=role)

@adminBP.route('/approve/<int:id>', methods=['POST'])
def approve(id):
    role = session.get('admin_role')
    convener = OConvener.query.get(id)
    if not convener:
        return redirect(url_for('admin.dashboard'))

    if role == 'eadmin':
        convener.status_text = 'reviewed'
    elif role == 'senior':
        convener.status_text = 'approved'

    db.session.commit()
    return redirect(url_for('admin.dashboard'))


@adminBP.route('/admin/reject/<int:id>', methods=['POST'])
def reject(id):
    role = session.get('admin_role')
    convener = OConvener.query.get(id)
    if not convener:
        return redirect(url_for('admin.dashboard'))

    # ✅ E-Admin 拒绝直接标记为 rejected
    if role in ['eadmin', 'senior']:
        convener.status_text = 'rejected'

    db.session.commit()
    return redirect(url_for('admin.dashboard'))

# 退出
@adminBP.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.admin_login'))
