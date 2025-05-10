from flask import Blueprint, render_template, request, session, redirect, url_for, current_app, send_from_directory
from app.models.E_admin import EAdmin
from app.models.Senior_E_Admin import SeniorEAdmin
from app.models.o_convener import OConvener
from app.models.base import db
from app.controller.log import log_access  # ✅ 添加日志记录函数

senioradminBP = Blueprint('senioradmin', __name__)

# 管理后台界面
@senioradminBP.route('/dashboard')
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
    return render_template('senior_admin_dashboard.html', conv_list=conv_list, role=role)


@senioradminBP.route('/approve/<int:id>', methods=['POST'])
def approve(id):
    role = session.get('admin_role')
    convener = OConvener.query.get(id)
    if not convener:
        return redirect(url_for('senioradmin.dashboard'))

    if role == 'eadmin':
        convener.status_text = 'reviewed'
        log_access(f"E-Admin 审核通过注册申请（O-Convener ID: {id}）")
    elif role == 'senior':
        convener.status_text = 'approved'
        log_access(f"Senior E-Admin 审核通过注册申请（O-Convener ID: {id}）")

    db.session.commit()
    return redirect(url_for('senioradmin.dashboard'))


@senioradminBP.route('/admin/reject/<int:id>', methods=['POST'])
def reject(id):
    role = session.get('admin_role')
    convener = OConvener.query.get(id)
    if not convener:
        return redirect(url_for('senioradmin.dashboard'))

    if role in ['eadmin', 'senior']:
        convener.status_text = 'rejected'
        log_access(f"{role} 拒绝了 O-Convener 的申请（ID: {id}）")

    db.session.commit()
    return redirect(url_for('senioradmin.dashboard'))


# 退出
@senioradminBP.route('/logout')
def logout():
    log_access("管理员退出登录")  # ✅ 记录登出
    session.clear()
    return redirect(url_for('admin.admin_login'))

@senioradminBP.route('/download_proof/<filename>')
def download_proof(filename):
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    return send_from_directory(upload_folder, filename, as_attachment=True)
